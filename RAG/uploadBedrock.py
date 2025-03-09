import json
import os
import boto3
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def convert_to_bedrock_kb_format(input_file, output_file):
    """
    Convert the JSON structure with embeddings to Bedrock Knowledge Base format.
    
    Args:
        input_file: Path to the input JSON file with embeddings
        output_file: Path to save the output JSON file in Bedrock KB format
    """
    print(f"Loading data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Data loaded successfully with {len(data.get('documents', []))} documents and {len(data.get('images', []))} images")
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Create Bedrock KB format entries
    kb_entries = []
    
    # Process documents
    print("\nConverting documents to KB format...")
    for doc in tqdm(data['documents']):
        if 'embedding' in doc and doc['content_type'] == 'document':
            kb_entry = {
                "id": doc['document_id'],  # Use document_id as the unique identifier
                "vectorField": {
                    "vector": doc['embedding'],
                    "dimensions": len(doc['embedding'])
                },
                "textField": doc.get('cleaned_text', ''),  # Original text content
                "metadataField": {
                    "document_id": doc['document_id'],
                    "title": doc.get('title', ''),
                    "url": doc.get('url', ''),
                    "content_type": "document"
                }
            }
            kb_entries.append(kb_entry)
    
    # Process images
    print("\nConverting images to KB format...")
    for img in tqdm(data['images']):
        if 'embedding' in img and img['content_type'] == 'image':
            kb_entry = {
                "id": img['image_id'],  # Use image_id as the unique identifier
                "vectorField": {
                    "vector": img['embedding'],
                    "dimensions": len(img['embedding'])
                },
                "textField": img.get('description', ''),  # Image description
                "metadataField": {
                    "document_id": img.get('document_id', ''),
                    "document_title": img.get('document_title', ''),
                    "content_type": "image",
                    "image_url": img.get('s3_url', '')
                }
            }
            kb_entries.append(kb_entry)
    
    # Save the KB format data
    print(f"Saving {len(kb_entries)} entries to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(kb_entries, f, ensure_ascii=False)
    
    print("Knowledge Base format data saved successfully")
    return kb_entries

def upload_to_s3(file_path, bucket_name, s3_key):
    """
    Upload a file to S3.
    
    Args:
        file_path: Local path to the file
        bucket_name: S3 bucket name
        s3_key: S3 object key (path in S3)
        
    Returns:
        str: S3 URL if successful, None otherwise
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('Home_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('Home_AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('Home_AWS_DEFAULT_REGION')
        )
        
        # Upload file to S3
        s3_client.upload_file(file_path, bucket_name, s3_key)
        
        # Return S3 URL
        return f"s3://{bucket_name}/{s3_key}"
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        return None

def main():
    # Configuration
    input_file = "RAG/Data/aws_structured_data_embeddings.json"
    output_file = "RAG/Data/bedrock_kb_format.json"
    
    # S3 configuration for KB data
    bucket_name = "renesas-rag"
    s3_key = "kb-data/bedrock_kb_format.json"
    
    # Convert to Bedrock KB format
    kb_entries = convert_to_bedrock_kb_format(input_file, output_file)
    
    if kb_entries:
        # Upload to S3
        print(f"\nUploading to S3 bucket: {bucket_name}")
        s3_url = upload_to_s3(output_file, bucket_name, s3_key)
        
        if s3_url:
            print(f"Successfully uploaded to: {s3_url}")
            print("\nYou can now use this S3 location when creating your Bedrock Knowledge Base.")
        else:
            print("Failed to upload to S3.")
    
if __name__ == "__main__":
    print("Starting conversion to Bedrock Knowledge Base format")
    main()
    print("Conversion completed")