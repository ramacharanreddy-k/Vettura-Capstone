import csv
import json
import os
from collections import defaultdict

def csv_to_nested_json(input_csv, output_json):
    """
    Convert CSV to nested JSON structure
    """
    # Initialize the nested dictionary
    nested_data = {}
    
    with open(input_csv, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            category_title = row['Category Title']
            category_url = row['Category URL']
            subcategory_title = row['Subcategory Title']
            
            # Split Topic URLs into a list
            topic_urls = row['Topic URLs'].split('|') if row['Topic URLs'] else []
            
            # Create category if it doesn't exist
            if category_title not in nested_data:
                nested_data[category_title] = {
                    'category_url': category_url,
                    'subcategories': {}
                }
            
            # Add subcategory information
            nested_data[category_title]['subcategories'][subcategory_title] = {
                'subcategory_url': row['Subcategory URL'],
                'article_count': int(row['Article Count']) if row['Article Count'].isdigit() else 0,
                'topic_urls': topic_urls
            }
    
    # Write to JSON file with proper formatting
    with open(output_json, 'w', encoding='utf-8') as file:
        json.dump(nested_data, file, indent=4, ensure_ascii=False)

def main():
    # File paths
    input_csv = os.path.join(os.path.dirname(__file__), "Data", "categories_with_topics.csv")
    output_json = os.path.join(os.path.dirname(__file__), "Data", "websiteMap.json")
    
    # Convert CSV to JSON
    csv_to_nested_json(input_csv, output_json)
    print(f"JSON file created successfully: {output_json}")

if __name__ == "__main__":
    main()