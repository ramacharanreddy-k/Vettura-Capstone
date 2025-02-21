import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import logging
from datetime import datetime
import time

def setup_logging():
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    log_file = os.path.join(logs_dir, f"crawler_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
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
        chrome_options.add_argument("--window-size=1920,1080")  # Added window size
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.implicitly_wait(10)
        logger.info("WebDriver setup successful")
        return driver
    except Exception as e:
        logger.error(f"Failed to setup WebDriver: {str(e)}")
        raise

def wait_for_element(driver, selector, timeout=10):
    """Helper function to wait for an element to be present"""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return element
    except Exception:
        return None

def extract_categories_and_subcategories(driver, logger):
    categories = []
    try:
        # Wait for the page to load
        time.sleep(5)  # Give Angular some time to render
        
        # Wait for Angular to fully load the content
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel.panel-default"))
        )
        
        # Give additional time for dynamic content to load
        time.sleep(2)
        
        # Find all category sections that actually contain content
        category_sections = driver.find_elements(By.CSS_SELECTOR, "div.panel.panel-default[style*='display: block']")
        if not category_sections:
            category_sections = driver.find_elements(By.CSS_SELECTOR, "div.panel.panel-default:not([style*='display: none'])")
        
        logger.info(f"Found {len(category_sections)} category sections")
        
        for section_index, category_section in enumerate(category_sections, 1):
            try:
                # Extract category information - using more specific selector
                category_element = category_section.find_element(By.CSS_SELECTOR, ".panel-heading h1.MainCategoryName.text-center a")
                category_title = category_element.text.strip()
                category_url = category_element.get_attribute("href")
                
                if not category_title:
                    logger.warning(f"Empty category title found in section {section_index}")
                    continue
                
                logger.info(f"Processing category {section_index}: {category_title}")
                
                # Extract subcategories - updated selector to match panel-body
                subcategory_elements = category_section.find_elements(
                    By.CSS_SELECTOR, ".panel-body .grid-item.cat-group"
                )
                
                subcategories = []
                for sub_index, subcategory_element in enumerate(subcategory_elements, 1):
                    try:
                        # Wait for subcategory element to be properly loaded
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "h2.h5.CategoryName a"))
                        )
                        
                        # Extract subcategory information with explicit text extraction
                        subcategory_title_element = subcategory_element.find_element(
                            By.CSS_SELECTOR, "h2.h5.CategoryName a"
                        )
                        
                        # Get text content with JavaScript for more reliable extraction
                        subcategory_title = driver.execute_script(
                            "return arguments[0].textContent;", 
                            subcategory_title_element
                        ).strip()
                        
                        # Skip if title is empty
                        if not subcategory_title:
                            logger.warning(f"Empty subcategory title found in category section {section_index}, subcategory {sub_index}")
                            continue
                            
                        subcategory_url = subcategory_title_element.get_attribute("href")
                        
                        # Extract article count from the last parentheses
                        article_count = 0
                        if '(' in subcategory_title and ')' in subcategory_title:
                            try:
                                # Find the last matching parentheses
                                last_close_paren = subcategory_title.rindex(')')
                                last_open_paren = subcategory_title.rindex('(')
                                
                                # Extract the content between the last set of parentheses
                                count_str = subcategory_title[last_open_paren + 1:last_close_paren]
                                
                                # Try to convert to integer
                                if count_str.isdigit():
                                    article_count = int(count_str)
                                    # Remove only the last parentheses with the count
                                    subcategory_title = subcategory_title[:last_open_paren].strip()
                                else:
                                    logger.warning(f"Found non-numeric content in last parentheses: {count_str}")
                            except ValueError as e:
                                logger.warning(f"Could not parse article count from: {subcategory_title}, Error: {str(e)}")
                            except Exception as e:
                                logger.error(f"Error processing title: {subcategory_title}, Error: {str(e)}")
                        
                        # Check for view more link
                        try:
                            view_more_element = subcategory_element.find_element(
                                By.CSS_SELECTOR, "div.more-link a"
                            )
                            view_more_url = view_more_element.get_attribute("href")
                            view_more_exists = True
                        except:
                            view_more_url = None
                            view_more_exists = False
                        
                        subcategories.append({
                            "subcategory_title": subcategory_title,
                            "subcategory_url": subcategory_url,
                            "view_more_exists": view_more_exists,
                            "view_more_url": view_more_url,
                            "article_count": article_count
                        })
                        
                        logger.info(f"  Processed subcategory {sub_index}: {subcategory_title}")
                        
                    except Exception as e:
                        logger.error(f"Error processing subcategory {sub_index}: {str(e)}")
                        continue
                
                categories.append({
                    "category_title": category_title,
                    "category_url": category_url,
                    "subcategories": subcategories
                })
                
            except Exception as e:
                logger.error(f"Error processing category section {section_index}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error in main extraction process: {str(e)}")
        
    return categories

def save_categories_to_csv(output_file, categories, logger):
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Category Title", "Category URL", "Subcategory Title", 
                "Subcategory URL", "View More Exists", "View More URL",
                "Article Count"
            ])
            
            for category in categories:
                for subcategory in category["subcategories"]:
                    writer.writerow([
                        category["category_title"],
                        category["category_url"],
                        subcategory["subcategory_title"],
                        subcategory["subcategory_url"],
                        subcategory["view_more_exists"],
                        subcategory["view_more_url"],
                        subcategory["article_count"]
                    ])
                    
        logger.info(f"Successfully saved data to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving to CSV: {str(e)}")
        raise

def main():
    logger = setup_logging()
    logger.info("Starting the scraper")
    
    # Configuration
    BASE_URL = "https://en-support.renesas.com/knowledgeBase"
    OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "Data", "categories_data.csv")
    
    driver = None
    try:
        # Setup WebDriver
        driver = setup_driver()
        
        # Navigate to the page
        logger.info(f"Navigating to {BASE_URL}")
        driver.get(BASE_URL)
        
        # Extract data
        categories = extract_categories_and_subcategories(driver, logger)
        
        # Save data
        if categories:
            save_categories_to_csv(OUTPUT_FILE, categories, logger)
            logger.info("Scraping completed successfully")
        else:
            logger.error("No categories were extracted")
        
    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")
        
    finally:
        if driver:
            driver.quit()
            logger.info("WebDriver closed")

if __name__ == "__main__":
    main()