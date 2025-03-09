import logging
import os
from datetime import datetime
import sys

# Create a singleton logger instance
_logger = None

def setup_logger():
    """Configure and return a logger instance"""
    global _logger
    
    # Return existing logger if already configured
    if _logger is not None:
        return _logger

    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    os.makedirs(logs_dir, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(logs_dir, f'scraper_{timestamp}.log')

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(module)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Setup logger
    _logger = logging.getLogger('knowledge_base_scraper')
    _logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    _logger.handlers = []
    
    # Add our handlers
    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)
    
    # Prevent logging from propagating to the root logger
    _logger.propagate = False

    return _logger

# Example usage
if __name__ == "__main__":
    logger = setup_logger()
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")