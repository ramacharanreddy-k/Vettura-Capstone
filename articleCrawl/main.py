import os
import json
from categoryManager import CategoryManager
from utils import load_config, ensure_directory
from logger import setup_logger

logger = setup_logger()

def main():
    try:
        # Load configuration
        config_path = os.path.join('config', 'config.json')
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found at {config_path}")
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
            
        config = load_config(config_path)
        
        # Ensure required directories exist
        for dir_path in config['directories'].values():
            ensure_directory(dir_path)
            logger.debug(f"Ensured directory exists: {dir_path}")
        
        # Initialize category manager
        manager = CategoryManager(
            base_dir=config['directories']['base_dir'],
            wait_time=config['wait_time']
        )
        
        # Load category data from JSON file one directory up
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(script_dir, '..', 'layoutCrawl', 'Data', 'websiteMap.json')
            
            if not os.path.exists(json_path):
                logger.error(f"Website map JSON not found at {json_path}")
                raise FileNotFoundError(f"Website map JSON not found at {json_path}")
            
            logger.info(f"Loading website map from: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                categories_data = json.load(f)
            
            # Validate categories data
            if not isinstance(categories_data, dict):
                raise ValueError("Categories data must be a dictionary")
            
            if not categories_data:
                raise ValueError("Categories data is empty")
            
            # Log categories found
            category_count = len(categories_data)
            logger.info(f"Found {category_count} categories to process")
            
            # Process all categories
            manager.process_categories(categories_data)
            logger.info("Scraping completed successfully")
            
        except FileNotFoundError as e:
            logger.error(f"File not found error: {str(e)}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from websiteMap.json: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Critical error in main process: {str(e)}")
        raise
    
if __name__ == "__main__":
    import sys
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        sys.exit(1)