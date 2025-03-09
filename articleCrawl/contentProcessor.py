import os
import json
import requests
import hashlib
from urllib.parse import urljoin, urlparse
from datetime import datetime
from logger import setup_logger
from htmlScrapper import HTMLScraper

logger = setup_logger()

class ContentProcessor:
    def __init__(self, base_dir):
        """Initialize content processor"""
        self.base_dir = base_dir
        self.html_scraper = HTMLScraper()
        
    def create_category_structure(self, category_name):
        """Create base directory for a specific category"""
        # Sanitize category name for filesystem
        safe_category = self.sanitize_filename(category_name)
        
        # Create category base directory
        category_dir = os.path.join(self.base_dir, "categories", safe_category)
        
        # Create metadata directory within category
        metadata_dir = os.path.join(category_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)
        
        return {"base": category_dir, "metadata": metadata_dir}
        
    def sanitize_filename(self, filename):
        """Convert string to valid filename"""
        valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        filename = ''.join(c for c in filename if c in valid_chars)
        return filename.replace(' ', '_').lower()
        
    def get_content_path(self, category_dirs, content_type, filename):
        """Get full path for content file within category structure"""
        return os.path.join(category_dirs[content_type], filename)
        
    def get_extension(self, url, content_type):
        """Get file extension from URL or content type"""
        # Try to get extension from URL first
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']:
            return ext
            
        # Fall back to content-type mapping
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'application/pdf': '.pdf'
        }
        return content_type_map.get(content_type.lower(), '.unknown')
        
    def download_file(self, url, save_dir):
        """Download a file and save it in the specified directory"""
        try:
            if not bool(urlparse(url).netloc):
                return None
                
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                # Get file extension and generate unique filename
                content_type_header = response.headers.get('content-type', '')
                ext = self.get_extension(url, content_type_header)
                filename = f"{hashlib.md5(url.encode()).hexdigest()}{ext}"
                
                # Get full path within the save directory
                local_path = os.path.join(save_dir, filename)
                
                # Save file
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                return {
                    "original_url": url,
                    "local_path": local_path,
                    "filename": filename,
                    "content_type": content_type_header
                }
                
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {str(e)}")
            return None
            
    def process_article(self, driver, article_url, category_name, subcategory_name):
        """Process an article and save its content in a dedicated folder"""
        try:
            # Create/get category and subcategory directory structure
            category_dirs = self.create_category_structure(category_name)
            subcategory_dir = os.path.join(category_dirs["base"], self.sanitize_filename(subcategory_name))
            os.makedirs(subcategory_dir, exist_ok=True)

            # Generate unique article ID and create article folder
            article_id = hashlib.md5(article_url.encode()).hexdigest()
            article_folder = os.path.join(subcategory_dir, self.sanitize_filename(article_id))
            os.makedirs(article_folder, exist_ok=True)

            # Create subfolders for the article
            article_subfolders = {
                "images": os.path.join(article_folder, "images"),
                "pdfs": os.path.join(article_folder, "pdfs"),
                "tables": os.path.join(article_folder, "tables"),
                "metadata": os.path.join(article_folder, "metadata")
            }
            for folder in article_subfolders.values():
                os.makedirs(folder, exist_ok=True)

            # Extract content
            article_content = self.html_scraper.extract_article_content(driver, article_url, article_subfolders["images"])
            if not article_content:
                return None

            # Save metadata
            metadata_path = os.path.join(article_subfolders["metadata"], "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(article_content["metadata"], f, ensure_ascii=False, indent=2)

            # Save full article content
            content_path = os.path.join(article_folder, "content.json")
            with open(content_path, 'w', encoding='utf-8') as f:
                json.dump(article_content, f, ensure_ascii=False, indent=2)

            # Download and save PDFs, tables, etc.
            for pdf_url in article_content["content"].get("pdfs", []):
                self.download_file(pdf_url, article_subfolders["pdfs"])

            for table in article_content["content"].get("tables", []):
                table_path = os.path.join(article_subfolders["tables"], f"table_{hashlib.md5(str(table).encode()).hexdigest()}.json")
                with open(table_path, 'w', encoding='utf-8') as f:
                    json.dump(table, f, ensure_ascii=False, indent=2)

            return article_content

        except Exception as e:
            logger.error(f"Error processing article {article_url}: {str(e)}")
            return None
            
    def process_subcategory(self, driver, category_name, subcategory_data):
        """Process all articles in a subcategory"""
        try:
            logger.info(f"Processing subcategory: {subcategory_data['subcategory_title']}")

            # Create/get category directory structure
            category_dirs = self.create_category_structure(category_name)

            # Create subcategory directory
            subcategory_dir = os.path.join(category_dirs["base"], self.sanitize_filename(subcategory_data['subcategory_title']))
            os.makedirs(subcategory_dir, exist_ok=True)

            # Save subcategory metadata
            metadata = {
                "category": category_name,
                "subcategory": subcategory_data['subcategory_title'],
                "url": subcategory_data['subcategory_url'],
                "article_count": len(subcategory_data.get('topic_urls', [])),
                "processed_at": datetime.utcnow().isoformat()
            }

            subcat_meta_path = os.path.join(subcategory_dir, "metadata.json")
            with open(subcat_meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # Process each article in the subcategory
            for article_url in subcategory_data.get('topic_urls', []):
                self.process_article(driver, article_url, category_name, subcategory_data['subcategory_title'])

        except Exception as e:
            logger.error(f"Error processing subcategory {subcategory_data['subcategory_title']}: {str(e)}")