import json
import os
import boto3
from tqdm import tqdm
from dotenv import load_dotenv
import numpy as np
import time

# Load environment variables
load_dotenv()

def initialize_bedrock_client():
    """Initialize AWS Bedrock client with office credentials."""
    print("Initializing AWS Bedrock client...")
    try:
        client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=os.environ.get("Office_AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("Office_AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("Office_AWS_DEFAULT_REGION")
        )
        print("AWS Bedrock client initialized successfully")
        return client
    except Exception as e:
        print(f"Error initializing AWS Bedrock client: {str(e)}")
        return None

def generate_titan_embedding(client, text, model_id):
    """
    Generate embedding for a text using AWS Bedrock Titan Embedding model.
    
    Args:
        client: AWS Bedrock client
        text: Text to generate embedding for
        model_id: Titan Embedding model ID
        
    Returns:
        List of embedding values or None if error
    """
    if not text:
        return None
        
    try:
        # Prepare the request body for the model
        request_body = json.dumps({
            "inputText": text
        })
        
        # Call the Bedrock runtime
        response = client.invoke_model(
            modelId=model_id,
            body=request_body
        )
        
        # Process the response
        response_body = json.loads(response.get('body').read())
        embedding = response_body.get('embedding')
        
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def process_data_for_embeddings(input_file, output_file, model_id):
    """
    Process the AWS structured data to add embeddings.
    
    Args:
        input_file: Path to the input JSON file (aws_structured_data_s3.json)
        output_file: Path to save the output JSON file with embeddings
        model_id: Titan Embedding model ID
    """
    print(f"Loading data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Data loaded successfully with {len(data.get('documents', []))} documents and {len(data.get('images', []))} images")
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Initialize Bedrock client
    bedrock_client = initialize_bedrock_client()
    if not bedrock_client:
        print("Failed to initialize Bedrock client. Exiting.")
        return
    
    # Process documents (text embeddings)
    print("\nGenerating embeddings for documents...")
    for i, doc in enumerate(tqdm(data['documents'])):
        if 'cleaned_text' in doc and doc['content_type'] == 'document':
            # Generate embedding for document text
            embedding = generate_titan_embedding(bedrock_client, doc['cleaned_text'], model_id)
            if embedding:
                doc['embedding'] = embedding
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
    
    # Process images (description embeddings)
    print("\nGenerating embeddings for image descriptions...")
    for i, img in enumerate(tqdm(data['images'])):
        if 'description' in img and img['content_type'] == 'image':
            # Generate embedding for image description
            embedding = generate_titan_embedding(bedrock_client, img['description'], model_id)
            if embedding:
                img['embedding'] = embedding
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.1)
    
    # Count items with embeddings
    docs_with_embeddings = sum(1 for doc in data['documents'] if 'embedding' in doc)
    images_with_embeddings = sum(1 for img in data['images'] if 'embedding' in img)
    
    print(f"\nGenerated embeddings for {docs_with_embeddings}/{len(data['documents'])} documents")
    print(f"Generated embeddings for {images_with_embeddings}/{len(data['images'])} images")
    
    # Save the enriched data
    print(f"Saving data with embeddings to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Data with embeddings saved successfully")

def main():
    # Configuration
    input_file = "RAG/Data/aws_structured_data_s3.json"
    output_file = "RAG/Data/aws_structured_data_embeddings.json"
    model_id = os.environ.get("TITAN_EMBEDDING_MODEL_ID")
    
    # Print configuration
    print("Configuration:")
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Model ID: {model_id}")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
    
    # Check if model ID is provided
    if not model_id:
        print("Error: TITAN_EMBEDDING_MODEL_ID not found in environment variables")
        return
    
    # Process data to add embeddings
    process_data_for_embeddings(input_file, output_file, model_id)

if __name__ == "__main__":
    print("Starting embedding generation")
    main()
    print("Embedding generation completed")