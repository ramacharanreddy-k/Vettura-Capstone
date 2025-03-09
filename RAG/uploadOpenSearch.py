import json
import os
import time
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration constants
DOCUMENT_INDEX = "renesas-documents"
IMAGE_INDEX = "renesas-images"
EMBEDDING_DIMENSION = 1536  # Set this to the actual dimension of your embeddings

def initialize_opensearch_client():
    """Initialize OpenSearch client with AWS credentials."""
    print("Initializing OpenSearch client...")
    
    try:
        # Get AWS credentials
        aws_access_key = os.environ.get("Home_AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("Home_AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("Home_AWS_DEFAULT_REGION")
        opensearch_endpoint = os.environ.get("OPENSEARCH_ENDPOINT")
        
        if not all([aws_access_key, aws_secret_key, aws_region, opensearch_endpoint]):
            print("Missing required environment variables for OpenSearch.")
            return None
        
        # Create AWS authentication
        aws_auth = AWS4Auth(
            aws_access_key,
            aws_secret_key,
            aws_region,
            'es'  # The service name for OpenSearch
        )
        
        # Initialize OpenSearch client
        client = OpenSearch(
            hosts=[{'host': opensearch_endpoint, 'port': 443}],
            http_auth=aws_auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )
        
        print("OpenSearch client initialized successfully")
        return client
        
    except Exception as e:
        print(f"Error initializing OpenSearch client: {str(e)}")
        return None

def create_index_if_not_exists(client, index_name, embedding_dimension):
    """Create an OpenSearch index with vector search capabilities if it doesn't exist."""
    try:
        # Check if the index exists
        if client.indices.exists(index=index_name):
            print(f"Index '{index_name}' already exists")
            return True
        
        # Define index mappings for vector search
        index_body = {
            "settings": {
                "index.knn": True,
                "number_of_shards": 3,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": embedding_dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib"
                        }
                    },
                    # Common fields for both document and image indices
                    "content_type": {"type": "keyword"},
                    "id": {"type": "keyword"},
                    
                    # Document-specific fields
                    "document_id": {"type": "keyword"},
                    "title": {"type": "text"},
                    "url": {"type": "keyword"},
                    "cleaned_text": {"type": "text"},
                    
                    # Image-specific fields
                    "image_id": {"type": "keyword"},
                    "document_title": {"type": "text"},
                    "local_path": {"type": "keyword"},
                    "s3_key": {"type": "keyword"},
                    "s3_url": {"type": "keyword"},
                    "description": {"type": "text"}
                }
            }
        }
        
        # Create the index
        client.indices.create(index=index_name, body=index_body)
        print(f"Created index '{index_name}' with vector search capabilities")
        return True
        
    except Exception as e:
        print(f"Error creating index '{index_name}': {str(e)}")
        return False

def upload_documents_to_opensearch(client, data, document_index, image_index):
    """Upload documents and images to OpenSearch indices."""
    
    # Upload documents
    print("\nUploading documents to OpenSearch...")
    doc_success = 0
    doc_failures = 0
    
    for doc in tqdm(data['documents']):
        # Skip if no embedding
        if 'embedding' not in doc:
            print(f"Skipping document {doc.get('document_id', 'unknown')} - no embedding")
            doc_failures += 1
            continue
        
        # Prepare document for indexing
        doc_id = doc.get('document_id')
        if not doc_id:
            print(f"Skipping document - no document_id")
            doc_failures += 1
            continue
            
        try:
            # Index the document
            response = client.index(
                index=document_index,
                body=doc,
                id=doc_id,
                refresh=True
            )
            
            if response.get('result') in ['created', 'updated']:
                doc_success += 1
            else:
                print(f"Failed to index document {doc_id}: {response}")
                doc_failures += 1
                
        except Exception as e:
            print(f"Error indexing document {doc_id}: {str(e)}")
            doc_failures += 1
    
    # Upload images
    print("\nUploading images to OpenSearch...")
    img_success = 0
    img_failures = 0
    
    for img in tqdm(data['images']):
        # Skip if no embedding
        if 'embedding' not in img:
            print(f"Skipping image {img.get('image_id', 'unknown')} - no embedding")
            img_failures += 1
            continue
        
        # Prepare image for indexing
        img_id = img.get('image_id')
        if not img_id:
            print(f"Skipping image - no image_id")
            img_failures += 1
            continue
            
        try:
            # Index the image
            response = client.index(
                index=image_index,
                body=img,
                id=img_id,
                refresh=True
            )
            
            if response.get('result') in ['created', 'updated']:
                img_success += 1
            else:
                print(f"Failed to index image {img_id}: {response}")
                img_failures += 1
                
        except Exception as e:
            print(f"Error indexing image {img_id}: {str(e)}")
            img_failures += 1
    
    return {
        'documents': {'success': doc_success, 'failures': doc_failures},
        'images': {'success': img_success, 'failures': img_failures}
    }

def test_knn_search(client, index_name, query_vector, k=5):
    """Test KNN search on the index."""
    try:
        print(f"\nTesting KNN search on index '{index_name}'...")
        
        # Construct the KNN query
        knn_query = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": {
                        "vector": query_vector,
                        "k": k
                    }
                }
            }
        }
        
        # Execute the search
        response = client.search(
            body=knn_query,
            index=index_name
        )
        
        # Extract and return results
        hits = response['hits']['hits']
        print(f"Found {len(hits)} results")
        
        # Print the top results
        for i, hit in enumerate(hits):
            score = hit['_score']
            source = hit['_source']
            
            if index_name == DOCUMENT_INDEX:
                print(f"{i+1}. Document: {source.get('title', 'No title')} (Score: {score})")
            else:
                print(f"{i+1}. Image: {source.get('document_title', 'No title')} (Score: {score})")
                
        return hits
        
    except Exception as e:
        print(f"Error testing KNN search: {str(e)}")
        return []

def main():
    """Main function to upload data to OpenSearch."""
    # Configuration
    input_file = "RAG/Data/aws_structured_data_embeddings.json"
    
    # Print configuration
    print("Configuration:")
    print(f"Input file: {input_file}")
    print(f"Document index: {DOCUMENT_INDEX}")
    print(f"Image index: {IMAGE_INDEX}")
    print(f"Embedding dimension: {EMBEDDING_DIMENSION}")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
    
    # Check for OpenSearch endpoint
    if not os.environ.get("OPENSEARCH_ENDPOINT"):
        print("Error: OPENSEARCH_ENDPOINT not found in environment variables")
        return
    
    # Load data
    print(f"Loading data from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Data loaded successfully with {len(data.get('documents', []))} documents and {len(data.get('images', []))} images")
    except Exception as e:
        print(f"Error loading data: {str(e)}")
        return
    
    # Check if there are embeddings
    docs_with_embeddings = sum(1 for doc in data['documents'] if 'embedding' in doc)
    images_with_embeddings = sum(1 for img in data['images'] if 'embedding' in img)
    
    print(f"Found {docs_with_embeddings}/{len(data['documents'])} documents with embeddings")
    print(f"Found {images_with_embeddings}/{len(data['images'])} images with embeddings")
    
    if docs_with_embeddings == 0 and images_with_embeddings == 0:
        print("Error: No embeddings found in the data")
        return
    
    # Initialize OpenSearch client
    client = initialize_opensearch_client()
    if not client:
        return
    
    # Create indices if they don't exist
    doc_index_created = create_index_if_not_exists(client, DOCUMENT_INDEX, EMBEDDING_DIMENSION)
    img_index_created = create_index_if_not_exists(client, IMAGE_INDEX, EMBEDDING_DIMENSION)
    
    if not doc_index_created or not img_index_created:
        print("Error: Failed to create one or more indices")
        return
    
    # Upload data to OpenSearch
    upload_results = upload_documents_to_opensearch(client, data, DOCUMENT_INDEX, IMAGE_INDEX)
    
    # Print summary
    print("\nUpload Summary:")
    print(f"Documents: {upload_results['documents']['success']} successful, {upload_results['documents']['failures']} failed")
    print(f"Images: {upload_results['images']['success']} successful, {upload_results['images']['failures']} failed")
    
    # Test search if there are successful uploads
    if upload_results['documents']['success'] > 0:
        print("\nWaiting 5 seconds for indices to be ready...")
        time.sleep(5)
        
        # Get a sample embedding for testing
        sample_doc = next((doc for doc in data['documents'] if 'embedding' in doc), None)
        if sample_doc:
            test_knn_search(client, DOCUMENT_INDEX, sample_doc['embedding'], k=3)
    
    if upload_results['images']['success'] > 0:
        # Get a sample image embedding for testing
        sample_img = next((img for img in data['images'] if 'embedding' in img), None)
        if sample_img:
            test_knn_search(client, IMAGE_INDEX, sample_img['embedding'], k=3)
    
    print("\nOpenSearch upload process completed")

if __name__ == "__main__":
    print("Starting OpenSearch upload")
    main()
    print("OpenSearch upload completed")