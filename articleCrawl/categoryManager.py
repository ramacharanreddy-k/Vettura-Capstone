from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from contentProcessor import ContentProcessor
from logger import setup_logger
import os
import json
import time
from datetime import datetime

logger = setup_logger()

class CategoryManager:
    def __init__(self, base_dir, wait_time=5):
        """
        Initialize the category manager.
        
        Args:
            base_dir (str): Base directory for storing all content
            wait_time (int): Time to wait between requests
        """
        self.base_dir = base_dir
        self.wait_time = wait_time
        self.content_processor = ContentProcessor(base_dir)
        self.driver = None
        
    def setup_driver(self):
        """Set up the Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
    def process_category(self, category_name, category_data):
        """
        Process a complete category and all its subcategories.
        
        Args:
            category_name (str): Name of the category
            category_data (dict): Category information including all subcategories
        """
        try:
            logger.info(f"Starting to process category: {category_name}")
            
            # Create base category directories using ContentProcessor
            category_dirs = self.content_processor.create_category_structure(category_name)
            
            # Ensure the metadata directory exists
            metadata_dir = os.path.join(category_dirs["base"], "metadata")
            os.makedirs(metadata_dir, exist_ok=True)
            
            # Save category metadata
            metadata = {
                "name": category_name,
                "url": category_data["category_url"],
                "subcategory_count": len(category_data["subcategories"]),
                "processed_at": datetime.utcnow().isoformat()
            }
            
            meta_path = os.path.join(metadata_dir, "category_meta.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Process each subcategory
            for subcat_name, subcat_data in category_data["subcategories"].items():
                logger.info(f"Processing subcategory: {subcat_name}")
                
                # Create subcategory directory
                subcategory_dir = os.path.join(category_dirs["base"], self.content_processor.sanitize_filename(subcat_name))
                os.makedirs(subcategory_dir, exist_ok=True)
                
                # Save subcategory metadata
                subcategory_info = {
                    "subcategory_title": subcat_name,
                    "subcategory_url": subcat_data["subcategory_url"],
                    "topic_urls": subcat_data["topic_urls"]
                }
                
                self.content_processor.process_subcategory(
                    self.driver,
                    category_name,
                    subcategory_info
                )
                
                time.sleep(self.wait_time)  # Be nice to the server
                
            logger.info(f"Completed processing category: {category_name}")
            
        except Exception as e:
            logger.error(f"Error processing category {category_name}: {str(e)}")
            
    def process_categories(self, categories_data):
        """
        Process multiple categories.
        
        Args:
            categories_data (dict): Dictionary of all categories to process
        """
        try:
            self.setup_driver()
            
            for category_name, category_data in categories_data.items():
                self.process_category(category_name, category_data)
                
        finally:
            if self.driver:
                self.driver.quit()