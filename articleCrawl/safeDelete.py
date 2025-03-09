import os
import shutil
from logger import setup_logger

logger = setup_logger()

def check_and_delete_incomplete_articles(base_dir, dry_run=True):
    """
    Recursively check each article folder under the specified base directory.
    If content.json is missing, delete the article folder.
    
    Args:
        base_dir (str): Base directory where categories are stored
        dry_run (bool): If True, only log actions without deleting anything
    """
    try:
        logger.info(f"Starting to check for content.json in: {base_dir}")
        if dry_run:
            logger.info("Dry run mode enabled. No folders will be deleted.")
        
        # Walk through the directory structure
        for root, dirs, files in os.walk(base_dir):
            # Calculate the depth of the current folder
            depth = root[len(base_dir):].count(os.sep)
            
            # Only process folders at the final depth (Level 6)
            if depth == 6:
                # Check if this is an article folder (contains subfolders like images, pdfs, etc.)
                if any(subfolder in dirs for subfolder in ["images", "pdfs", "tables", "metadata"]):
                    # Check if content.json exists
                    content_json_path = os.path.join(root, "content.json")
                    if not os.path.exists(content_json_path):
                        logger.warning(f"content.json missing in {root}. Deleting folder...")
                        if not dry_run:
                            shutil.rmtree(root)
                            logger.info(f"Deleted folder: {root}")
                    else:
                        logger.info(f"content.json found in {root}")
        
        logger.info(f"Completed checking directory: {base_dir}")
    
    except Exception as e:
        logger.error(f"Error processing directory {base_dir}: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Set base_dir to the current directory
    base_dir = os.getcwd()  # This will set base_dir to "Vettura-Capstone"
    check_and_delete_incomplete_articles(base_dir, dry_run=False)  # Set dry_run=False to enable deletion