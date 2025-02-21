import os
import csv
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def setup_logging():
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, f"topic_extractor_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def setup_driver():
    logger = logging.getLogger(__name__)
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        logger.info("WebDriver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup WebDriver: {str(e)}")
        raise

def extract_article_urls(driver, subcategory_url, logger):
    """Extract all article URLs from a subcategory page"""
    article_urls = []
    try:
        logger.info(f"Visiting subcategory URL: {subcategory_url}")
        driver.get(subcategory_url)
        
        # Wait for the article links to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.article-links"))
        )
        
        # Give additional time for dynamic content
        time.sleep(2)
        
        # Find all article links
        article_elements = driver.find_elements(By.CSS_SELECTOR, "ul.article-links li.article-link a.article")
        
        for article in article_elements:
            try:
                url = article.get_attribute("href")
                if url:
                    article_urls.append(url)
            except Exception as e:
                logger.warning(f"Failed to get URL from article element: {str(e)}")
                continue
        
        logger.info(f"Found {len(article_urls)} article URLs")
        
    except Exception as e:
        logger.error(f"Error extracting articles from {subcategory_url}: {str(e)}")
    
    return article_urls

def process_csv(input_csv, output_csv, logger):
    """Process the input CSV and create new CSV with article URLs"""
    driver = None
    try:
        driver = setup_driver()
        
        # Read the existing CSV
        with open(input_csv, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows = list(reader)
        
        # Process each row
        total_rows = len(rows)
        for index, row in enumerate(rows, 1):
            logger.info(f"Processing row {index} of {total_rows}")
            
            subcategory_url = row.get('Subcategory URL')
            if not subcategory_url:
                logger.warning(f"No subcategory URL found in row {index}")
                row['Topic URLs'] = ''
                continue
            
            # Extract article URLs
            article_urls = extract_article_urls(driver, subcategory_url, logger)
            
            # Add article URLs to the row
            row['Topic URLs'] = '|'.join(article_urls) if article_urls else ''
        
        # Write the new CSV
        fieldnames = list(reader.fieldnames) + ['Topic URLs']
        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        logger.info(f"Successfully created new CSV: {output_csv}")
        
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        raise
    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver closed")

def main():
    logger = setup_logging()
    logger.info("Starting topic URL extraction")
    
    # File paths
    input_csv = os.path.join(os.path.dirname(__file__), "Data", "categories_data.csv")
    output_csv = os.path.join(os.path.dirname(__file__), "Data", "categories_with_topics.csv")
    
    try:
        process_csv(input_csv, output_csv, logger)
        logger.info("Topic URL extraction completed successfully")
    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")

if __name__ == "__main__":
    main()