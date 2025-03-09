from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import setup_logger
import re
from datetime import datetime
import time
import requests
import os
import hashlib
from urllib.parse import urljoin, urlparse

logger = setup_logger()

class HTMLScraper:
    def download_image(self, image_url, save_dir):
        """Download image and return local path"""
        try:
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                # Get file extension from URL or content-type
                content_type = response.headers.get('content-type', '')
                ext = self.get_file_extension(image_url, content_type)
                
                # Generate unique filename
                filename = f"{hashlib.md5(image_url.encode()).hexdigest()}{ext}"
                local_path = os.path.join(save_dir, filename)
                
                # Save image
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                return local_path
            return None
        except Exception as e:
            logger.error(f"Error downloading image from {image_url}: {str(e)}")
            return None

    def get_file_extension(self, url, content_type):
        """Get file extension from URL or content type"""
        # Try to get extension from URL first
        ext = os.path.splitext(urlparse(url).path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return ext
            
        # Fall back to content-type mapping
        content_type_map = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif'
        }
        return content_type_map.get(content_type.lower(), '.jpg')

    def extract_article_content(self, driver, article_url, save_dir):
        """Extract content from article HTML using specific selectors"""
        try:
            # Navigate to article and wait for Angular
            driver.get(article_url)
            time.sleep(2)
            
            # Wait for main content container
            main_content = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.col-lg-10.col-md-10"))
            )
            
            # Extract title
            title_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.row h2.ng-binding"))
            )
            title = title_element.text.strip()
            logger.info(f"Extracting content from article: {title}")
            
            # Find article body
            article_body = driver.find_element(By.CSS_SELECTOR, ".tiny-style-wrapper")
            
            # Initialize content storage
            content = {
                "sections": [],
                "images": [],
                "tables": [],
                "pdfs": [],
                "downloads": [],
                "related_products": [],
                "links": []
            }
            
            # Extract last updated date
            last_updated = None
            date_div = article_body.find_elements(By.CLASS_NAME, "latestUpdate")
            if date_div:
                date_text = date_div[0].text
                date_match = re.search(r'Last Updated:[ ]*(\d{2}/\d{2}/\d{4})', date_text)
                if date_match:
                    try:
                        last_updated = datetime.strptime(date_match.group(1), '%d/%m/%Y').strftime('%Y-%m-%d')
                    except ValueError:
                        pass
            
            # Process content sections
            all_elements = article_body.find_elements(By.XPATH, ".//*")
            current_section = {"type": "text", "content": ""}
            
            for element in all_elements:
                tag_name = element.tag_name.lower()
                
                # Handle images
                if tag_name == 'img':
                    # Save current text section if it exists
                    if current_section["content"].strip():
                        content["sections"].append(current_section)
                        current_section = {"type": "text", "content": ""}
                    
                    src = element.get_attribute('src')
                    if src:
                        image_data = {
                            "original_url": src,
                            "alt_text": element.get_attribute('alt') or "",
                            "width": element.get_attribute('width'),
                            "height": element.get_attribute('height')
                        }
                        
                        # Download image
                        local_path = self.download_image(src, save_dir)
                        if local_path:
                            image_data["local_path"] = local_path
                            content["images"].append(image_data)
                            # Add image reference to sections
                            content["sections"].append({
                                "type": "image",
                                "content": image_data
                            })
                
                # Handle text content
                elif tag_name in ['p', 'div', 'span']:
                    text = element.text.strip()
                    if text and not text.startswith("Last Updated"):
                        current_section["content"] = text
                        content["sections"].append(current_section)
                        current_section = {"type": "text", "content": ""}
                
                # Handle links
                elif tag_name == 'a':
                    href = element.get_attribute('href')
                    if href:
                        link_data = {
                            "text": element.text.strip(),
                            "url": href
                        }
                        if href.lower().endswith(('.pdf', '.zip', '.doc', '.docx')):
                            content["downloads"].append({
                                "type": href.split('.')[-1].lower(),
                                **link_data
                            })
                        elif href not in [l["url"] for l in content["links"]]:
                            content["links"].append(link_data)
            
            # Add last section if exists
            if current_section["content"].strip():
                content["sections"].append(current_section)
            
            # Extract tables and related products
            tables = article_body.find_elements(By.TAG_NAME, "table")
            for table in tables:
                table_data = {
                    "headers": [],
                    "rows": []
                }
                
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        row_data = [cell.text.strip() for cell in cells]
                        if any(row_data):  # Only add non-empty rows
                            table_data["rows"].append(row_data)
                            # Check if this is a product table
                            if row.get_attribute("bgcolor") == "#eeeee6":
                                for cell in cells:
                                    product = cell.text.strip()
                                    if product and product not in content["related_products"]:
                                        content["related_products"].append(product)
                
                if table_data["headers"] or table_data["rows"]:
                    content["tables"].append(table_data)
            
            return {
                "metadata": {
                    "url": article_url,
                    "title": title,
                    "last_updated": last_updated,
                    "extracted_at": datetime.utcnow().isoformat()
                },
                "content": content
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {article_url}: {str(e)}")
            return None