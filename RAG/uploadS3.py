import json
import os
import boto3
from botocore.exceptions import ClientError
from PIL import Image
import io
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
print("Environment variables loaded from .env file")

def upload_image_to_s3(s3_client, local_path, bucket_name, s3_key, base_dir=None):
    """
    Upload an image to S3, resizing if necessary.
    
    Args:
        s3_client: boto3 S3 client
        local_path: Local path to the image
        bucket_name: S3 bucket name
        s3_key: S3 object key (path in S3)
        base_dir: Base directory to prepend to local_path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Look for the file in different possible locations
        possible_paths = []
        
        # 1. Try the original path
        if base_dir:
            possible_paths.append(os.path.join(base_dir, local_path))
        else:
            possible_paths.append(local_path)
            
        # 2. Try removing "articleCrawl" from the path if it exists
        if base_dir and "articleCrawl" in base_dir:
            possible_paths.append(os.path.join(base_dir.replace("articleCrawl", ""), local_path))
            
        # 3. Try with "articleCrawl" explicitly in the path
        if base_dir:
            possible_paths.append(os.path.join(base_dir, "articleCrawl", local_path))

        # 4. Try looking in the directory structure assuming CWD is the project root
        possible_paths.append(local_path)
        
        # Print search paths for debugging
        print(f"Searching for file in the following locations:")
        for idx, path in enumerate(possible_paths):
            print(f"  Path {idx+1}: {path}")
        
        # Try each path until we find the file
        full_path = None
        for path in possible_paths:
            if os.path.exists(path):
                full_path = path
                print(f"File found at: {full_path}")
                break
                
        if not full_path:
            print(f"ERROR: File not found at any of the attempted locations")
            # List the directory contents to debug
            try:
                # Get the directory of the first possible path
                parent_dir = os.path.dirname(possible_paths[0])
                if os.path.exists(parent_dir):
                    print(f"Contents of parent directory {parent_dir}:")
                    for item in os.listdir(parent_dir):
                        print(f"  {item}")
                else:
                    print(f"Parent directory {parent_dir} does not exist")
            except Exception as e:
                print(f"Error listing directory contents: {str(e)}")
            return False
        
        # Open and resize the image
        try:
            img = Image.open(full_path)
            print(f"Image opened successfully: {img.format}, {img.size}")
            
            # Resize if larger than 1200px in either dimension, maintaining aspect ratio
            max_size = 1200
            if img.width > max_size or img.height > max_size:
                print(f"Resizing image from {img.size}")
                img.thumbnail((max_size, max_size))
                print(f"Resized to {img.size}")
            
            # Save to in-memory file
            buffer = io.BytesIO()
            if img.format:
                img.save(buffer, format=img.format)
                print(f"Saved image to buffer with format {img.format}")
            else:
                # Default to PNG if format is unknown
                img.save(buffer, format="PNG")
                print("Saved image to buffer with default format PNG")
            buffer.seek(0)
            
            # Upload to S3 without ACL parameter
            print(f"Uploading to S3: {bucket_name}/{s3_key}")
            try:
                s3_client.upload_fileobj(
                    buffer, 
                    bucket_name, 
                    s3_key,
                    ExtraArgs={
                        'ContentType': 'image/png'
                    }
                )
                print(f"Upload successful: {s3_key}")
                return True
            except ClientError as e:
                print(f"S3 upload error: {str(e)}")
                return False
        except Exception as e:
            print(f"Image processing error: {str(e)}")
            return False
            
    except Exception as e:
        print(f"General error: {str(e)}")
        return False

def upload_images(json_file, bucket_name, base_dir=None, region="us-east-1"):
    """
    Upload all images in the structured JSON to S3.
    
    Args:
        json_file: Path to the structured JSON file
        bucket_name: S3 bucket name
        base_dir: Base directory where images are stored locally
        region: AWS region
        
    Returns:
        dict: Updated images data with S3 URLs
    """
    # Load the JSON data
    print(f"Loading JSON data from: {json_file}")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"JSON loaded successfully with {len(data.get('images', []))} images")
    except Exception as e:
        print(f"Error loading JSON: {str(e)}")
        return None
    
    # Initialize S3 client using the specified environment variables
    print("Initializing S3 client...")
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('Home_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('Home_AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('Home_AWS_DEFAULT_REGION', region)
        )
        
        # Test S3 connection by listing buckets
        try:
            response = s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            print(f"S3 connection successful. Available buckets: {buckets}")
            
            # Check if our target bucket exists
            if bucket_name in buckets:
                print(f"Target bucket '{bucket_name}' found in your account")
            else:
                print(f"WARNING: Target bucket '{bucket_name}' not found in your account")
        except ClientError as e:
            print(f"Error checking S3 buckets: {str(e)}")
    
    except Exception as e:
        print(f"Error initializing S3 client: {str(e)}")
        return None
    
    # Process each image
    success_count = 0
    failure_count = 0
    
    # Check for the presence of the images directory structure
    print("\nChecking directory structure...")
    sample_dirs = [
        "data",
        "data/categories",
        "articleCrawl/data",
        "articleCrawl/data/categories"
    ]
    for dir_path in sample_dirs:
        full_path = os.path.join(base_dir, dir_path)
        print(f"Directory '{dir_path}': {'EXISTS' if os.path.exists(full_path) else 'NOT FOUND'}")
    
    # Process a subset of images to find working paths
    print("\nTesting sample image paths...")
    sample_count = min(5, len(data['images']))
    for i in range(sample_count):
        local_path = data['images'][i]['local_path']
        print(f"Testing sample image {i+1}: {local_path}")
        test_paths = [
            os.path.join(base_dir, local_path),
            os.path.join(base_dir, "articleCrawl", local_path),
            local_path
        ]
        for path in test_paths:
            exists = os.path.exists(path)
            print(f"  Path: {path} - {'EXISTS' if exists else 'NOT FOUND'}")
    
    # Let's try to find the correct base directory
    print("\nSearching for correct base directory...")
    
    # List of possible base directories
    possible_base_dirs = [
        base_dir,
        os.path.join(base_dir, "articleCrawl"),
        base_dir.replace("Vettura-Capstone", ""),
        os.path.dirname(base_dir)
    ]
    
    correct_base_dir = None
    for test_dir in possible_base_dirs:
        print(f"Testing base directory: {test_dir}")
        if os.path.exists(test_dir):
            # Try to find a sample image with this base dir
            for i in range(min(10, len(data['images']))):
                test_path = os.path.join(test_dir, data['images'][i]['local_path'])
                if os.path.exists(test_path):
                    print(f"Found a match! Image exists at: {test_path}")
                    correct_base_dir = test_dir
                    break
        if correct_base_dir:
            break
    
    if correct_base_dir:
        print(f"Using correct base directory: {correct_base_dir}")
        base_dir = correct_base_dir
    else:
        print("Could not find a working base directory. Will try multiple paths for each image.")
    
    # Now process all images
    for i, image in enumerate(tqdm(data['images'], desc="Uploading images to S3")):
        local_path = image['local_path']
        s3_key = image['s3_key']
        
        print(f"\nProcessing image {i+1}/{len(data['images'])}: {local_path}")
        
        if upload_image_to_s3(s3_client, local_path, bucket_name, s3_key, base_dir):
            # Add S3 URL to the image data
            image['s3_url'] = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"
            success_count += 1
        else:
            failure_count += 1
    
    print(f"\nUploads completed: {success_count} successful, {failure_count} failed")
    
    # Save the updated JSON with S3 URLs
    output_file = json_file.replace('.json', '_s3.json')
    print(f"Saving updated JSON to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    return data

def main():
    # Configuration
    json_file = "RAG/Data/aws_structured_data.json"
    bucket_name = "renesas-rag"  # Using the specified bucket name
    base_dir = os.getcwd()  # Use current directory as base
    
    # Print current working directory and check if files exist
    print(f"Current working directory: {base_dir}")
    print(f"JSON file exists: {os.path.exists(json_file)}")
    
    # Verify AWS credentials
    if not os.environ.get('Home_AWS_ACCESS_KEY_ID') or not os.environ.get('Home_AWS_SECRET_ACCESS_KEY'):
        print("ERROR: AWS credentials not found in environment variables")
        return
    
    # Check that the JSON file exists and has the expected structure
    if not os.path.exists(json_file):
        print(f"ERROR: JSON file not found: {json_file}")
        return
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            if 'images' not in data:
                print(f"ERROR: JSON file does not contain 'images' key")
                return
            print(f"Found {len(data['images'])} images in JSON file")
    except Exception as e:
        print(f"ERROR: Could not parse JSON file: {str(e)}")
        return
    
    # Upload images to S3
    print(f"Starting upload to bucket: {bucket_name}")
    upload_images(json_file, bucket_name, base_dir)

if __name__ == "__main__":
    print("Starting uploadS3.py")
    main()
    print("Script execution completed")