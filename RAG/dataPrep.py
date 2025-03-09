import pandas as pd
import json
import os
import hashlib
import ast
from tqdm import tqdm

def fix_data_types(df):
    """
    Fix the data types in the DataFrame - convert strings to their proper types.
    
    Args:
        df: DataFrame with string fields that should be parsed
        
    Returns:
        DataFrame with corrected data types
    """
    fixed_df = df.copy()
    
    # Sample a row to check data formats
    sample_row = fixed_df.iloc[0]
    print("Original data types:")
    print(f"metadata type: {type(sample_row.get('metadata'))}")
    print(f"image_paths type: {type(sample_row.get('image_paths'))}")
    print(f"image_descriptions type: {type(sample_row.get('image_descriptions'))}")
    
    # Try to safely parse the metadata string to a dictionary (if it's a string)
    def parse_metadata(meta_str):
        if isinstance(meta_str, dict):
            return meta_str
        
        try:
            # Try using ast.literal_eval which is safer than eval
            return ast.literal_eval(meta_str)
        except (ValueError, SyntaxError, TypeError):
            try:
                # If that fails, try regular json parsing
                return json.loads(meta_str)
            except:
                # If all parsing fails, return an empty dict
                return {}
    
    # Try to safely parse lists (if they're strings)
    def parse_list(list_str):
        if isinstance(list_str, list):
            return list_str
        
        try:
            # Try using ast.literal_eval
            return ast.literal_eval(list_str)
        except (ValueError, SyntaxError, TypeError):
            try:
                # If that fails, try regular json parsing
                return json.loads(list_str)
            except:
                # If all parsing fails, return an empty list
                return []
    
    # Apply the parsers
    print("Fixing data types...")
    fixed_df['metadata'] = fixed_df['metadata'].apply(parse_metadata)
    fixed_df['image_paths'] = fixed_df['image_paths'].apply(parse_list)
    fixed_df['image_descriptions'] = fixed_df['image_descriptions'].apply(parse_list)
    
    # Check the fixed data types
    sample_row = fixed_df.iloc[0]
    print("\nFixed data types:")
    print(f"metadata type: {type(sample_row.get('metadata'))}")
    print(f"image_paths type: {type(sample_row.get('image_paths'))}")
    print(f"image_descriptions type: {type(sample_row.get('image_descriptions'))}")
    
    # Count images
    total_images = fixed_df['image_paths'].apply(len).sum()
    print(f"\nTotal images after fixing: {total_images}")
    
    return fixed_df

def prepare_data_for_aws(df, output_file="RAG/Data/aws_structured_data.json"):
    """
    Convert the fixed dataframe to a structured JSON format suitable for AWS services.
    
    Args:
        df: DataFrame with proper data types
        output_file: Path to save the JSON output
        
    Returns:
        dict: Counts of documents and images processed
    """
    # Create the structure for the JSON
    documents = []
    images = []
    
    # Iterate through each row in the dataframe
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing documents"):
        doc_id = row['document_id']
        
        # Extract metadata
        metadata = row.get('metadata', {})
        title = ""
        url = ""
        
        if isinstance(metadata, dict):
            title = metadata.get('title', "")
            url = metadata.get('url', "")
        
        # Create document entry
        document = {
            "document_id": doc_id,
            "title": title,
            "url": url,
            "cleaned_text": row.get('cleaned_text', ""),
            "content_type": "document"
        }
        
        # Add to documents
        documents.append(document)
        
        # Process images
        image_paths = row.get('image_paths', [])
        image_descs = row.get('image_descriptions', [])
        
        # Only process if both are lists and not empty
        if isinstance(image_paths, list) and isinstance(image_descs, list):
            # Get the minimum length to avoid index errors
            min_length = min(len(image_paths), len(image_descs))
            
            # Print details for debugging
            if min_length > 0:
                print(f"Document {doc_id} has {min_length} images")
            
            for i in range(min_length):
                # Skip if either path or description is empty
                if not image_paths[i] or not image_descs[i]:
                    continue
                    
                # Create a unique ID for the image
                image_path = image_paths[i]
                image_id = hashlib.md5(f"{doc_id}_{image_path}".encode()).hexdigest()
                
                # Create image entry
                image = {
                    "image_id": image_id,
                    "document_id": doc_id,
                    "document_title": title,
                    "local_path": image_path,
                    "s3_key": f"images/{doc_id}/{image_id}.png",
                    "description": image_descs[i],
                    "content_type": "image"
                }
                
                # Add to images
                images.append(image)
    
    # Create the final structure
    structured_data = {
        "documents": documents,
        "images": images
    }
    
    # Save to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(documents)} documents and {len(images)} images to {output_file}")
    
    # Return counts for summary
    return {
        "document_count": len(documents),
        "image_count": len(images)
    }

if __name__ == "__main__":
    try:
        # Load the DataFrame
        print(f"Current Working Directory: {os.getcwd()}")
        df = pd.read_csv('Data/processed_data_images_descriptions.csv')
        print(f"Loaded DataFrame with {len(df)} rows")
        
        # Fix the data types
        fixed_df = fix_data_types(df)
        
        # Prepare the data for AWS
        counts = prepare_data_for_aws(fixed_df)
        
        print("\nData preparation complete!")
        print(f"Total documents: {counts['document_count']}")
        print(f"Total images: {counts['image_count']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()