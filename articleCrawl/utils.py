import os
import json
import hashlib
from urllib.parse import urlparse
from logger import setup_logger

logger = setup_logger()

def sanitize_filename(filename):
    """
    Convert string to valid filename.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    valid_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    filename = ''.join(c for c in filename if c in valid_chars)
    return filename.replace(' ', '_').lower()

def generate_file_id(url):
    """
    Generate unique ID for a file based on URL.
    
    Args:
        url (str): File URL
        
    Returns:
        str: MD5 hash of the URL
    """
    return hashlib.md5(url.encode()).hexdigest()

def load_config(config_path):
    """
    Load configuration from JSON file.
    
    Args:
        config_path (str): Path to config file
        
    Returns:
        dict: Configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            logger.debug(f"Successfully loaded config from {config_path}")
            return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading config: {str(e)}")
        raise

def ensure_directory(directory):
    """
    Create directory if it doesn't exist.
    
    Args:
        directory (str): Directory path to create
        
    Returns:
        bool: True if directory exists or was created successfully
    """
    try:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Ensured directory exists: {directory}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        raise

def get_file_extension(url, content_type):
    """
    Get file extension from URL or content type.
    
    Args:
        url (str): File URL
        content_type (str): Content-Type header value
        
    Returns:
        str: File extension including dot
    """
    # Try to get extension from URL first
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.pdf']:
        return ext
        
    # Fall back to content-type mapping
    content_type_map = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'application/pdf': '.pdf',
        'application/javascript': '.js',
        'text/css': '.css',
        'text/html': '.html',
        'text/plain': '.txt'
    }
    
    mapped_ext = content_type_map.get(content_type.lower(), '.unknown')
    if mapped_ext == '.unknown':
        logger.warning(f"Unknown content type: {content_type} for URL: {url}")
    
    return mapped_ext