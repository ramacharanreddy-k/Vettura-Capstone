import json
import boto3
import os
from dotenv import load_dotenv
import argparse
from typing import List, Dict, Any
import time

# Load environment variables
load_dotenv()

class BedrockRAG:
    def __init__(self, kb_id, llm_model_id, embedding_model_id, region="us-east-1"):
        """
        Initialize the Bedrock RAG system.
        
        Args:
            kb_id: Bedrock Knowledge Base ID
            llm_model_id: Bedrock LLM Model ID (e.g., Meta Llama)
            embedding_model_id: Bedrock Embedding Model ID (Titan)
            region: AWS region
        """
        # Initialize Bedrock clients
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            region_name=region,
            aws_access_key_id=os.environ.get('Home_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('Home_AWS_SECRET_ACCESS_KEY')
        )
        
        self.bedrock_agent = boto3.client(
            'bedrock-agent-runtime',
            region_name=region,
            aws_access_key_id=os.environ.get('Home_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('Home_AWS_SECRET_ACCESS_KEY')
        )
        
        self.kb_id = kb_id
        self.llm_model_id = llm_model_id
        self.embedding_model_id = embedding_model_id
        
        print(f"Initialized Bedrock RAG with Knowledge Base ID: {kb_id}")
        print(f"LLM Model: {llm_model_id}")
        print(f"Embedding Model: {embedding_model_id}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a text using Bedrock Titan Embedding model.
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            List of embedding values
        """
        if not text:
            return []
            
        try:
            # Prepare the request body for the model
            request_body = json.dumps({
                "inputText": text
            })
            
            # Call the Bedrock runtime
            response = self.bedrock_runtime.invoke_model(
                modelId=self.embedding_model_id,
                body=request_body
            )
            
            # Process the response
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding')
            
            return embedding
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return []
    
    def retrieve_from_kb(self, query: str, top_k: int = 3, score_threshold: float = 0.7) -> Dict[str, List[Dict]]:
        """
        Retrieve documents and images from Knowledge Base based on query.
        
        Args:
            query: User query
            top_k: Number of top results to retrieve for each content type
            score_threshold: Minimum similarity score to include in results
            
        Returns:
            Dictionary with document and image results
        """
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                print("Failed to generate embedding for query")
                return {"documents": [], "images": []}
            
            # Retrieve relevant documents from Knowledge Base
            response = self.bedrock_agent.retrieve(
                knowledgeBaseId=self.kb_id,
                retrievalQuery={
                    "vectorQuery": {
                        "vector": query_embedding,
                        "numberOfResults": top_k * 2  # Request more to filter by content type
                    }
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k * 2
                    }
                }
            )
            
            # Process retrieved results
            retrieved_results = response.get("retrievalResults", [])
            
            # Separate documents and images
            documents = []
            images = []
            
            for result in retrieved_results:
                # Extract content and metadata
                content = result.get("content", {}).get("text", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0)
                
                # Skip if score is below threshold
                if score < score_threshold:
                    continue
                
                # Determine content type
                content_type = metadata.get("content_type", "")
                
                result_data = {
                    "content": content,
                    "metadata": metadata,
                    "score": score
                }
                
                # Categorize by content type
                if content_type == "document":
                    documents.append(result_data)
                elif content_type == "image":
                    images.append(result_data)
            
            # Sort by score and limit to top_k for each type
            documents = sorted(documents, key=lambda x: x["score"], reverse=True)[:top_k]
            images = sorted(images, key=lambda x: x["score"], reverse=True)[:top_k]
            
            return {
                "documents": documents,
                "images": images
            }
        except Exception as e:
            print(f"Error retrieving from Knowledge Base: {str(e)}")
            return {"documents": [], "images": []}
    
    def generate_llm_response(self, query: str, retrieved_data: Dict[str, List[Dict]]) -> str:
        """
        Generate response using Bedrock LLM (Meta Llama) with retrieved data.
        
        Args:
            query: User query
            retrieved_data: Dictionary with document and image results
            
        Returns:
            LLM-generated response
        """
        try:
            # Create context from retrieved data
            context = "I'm providing you with relevant information to answer the query. Please use this information to provide a helpful response.\n\n"
            
            # Add document information
            if retrieved_data["documents"]:
                context += "DOCUMENTS:\n"
                for i, doc in enumerate(retrieved_data["documents"], 1):
                    context += f"Document {i}:\n"
                    context += f"Title: {doc['metadata'].get('title', 'Untitled')}\n"
                    context += f"Content: {doc['content']}\n\n"
            
            # Add image information
            if retrieved_data["images"]:
                context += "IMAGES:\n"
                for i, img in enumerate(retrieved_data["images"], 1):
                    context += f"Image {i}:\n"
                    context += f"Description: {img['content']}\n"
                    context += f"URL: {img['metadata'].get('image_url', '')}\n\n"
            
            # Create prompt for LLM
            prompt = f"""
Context:
{context}

User Query: {query}

Based on the information provided in the context, please provide a comprehensive answer to the user's query. 
If images are mentioned in the context, reference them in your answer if they're relevant to the query.
If the context doesn't contain enough information to answer the query, please state that and provide a general response based on your knowledge.

Answer:
"""
            
            # Call Bedrock LLM model
            request_body = json.dumps({
                "prompt": prompt,
                "max_gen_len": 1024,
                "temperature": 0.2,
                "top_p": 0.9
            })
            
            # Invoke the model
            response = self.bedrock_runtime.invoke_model(
                modelId=self.llm_model_id,
                body=request_body
            )
            
            # Parse the response
            response_body = json.loads(response.get('body').read())
            llm_response = response_body.get('generation', '')
            
            return llm_response
        except Exception as e:
            print(f"Error generating LLM response: {str(e)}")
            return f"I'm sorry, I couldn't generate a response due to an error: {str(e)}"
    
    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        End-to-end function to answer a user query using RAG.
        
        Args:
            query: User query
            
        Returns:
            Dictionary with response and retrieved data
        """
        print(f"Processing query: {query}")
        
        # Step 1: Retrieve relevant information from Knowledge Base
        print("Retrieving relevant information...")
        retrieved_data = self.retrieve_from_kb(query)
        
        # Step 2: Generate response using LLM
        print("Generating response...")
        response = self.generate_llm_response(query, retrieved_data)
        
        # Return response with retrieved data for transparency
        return {
            "query": query,
            "response": response,
            "retrieved_data": retrieved_data
        }

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Bedrock RAG System')
    parser.add_argument('--query', type=str, required=True, help='User query')
    parser.add_argument('--kb-id', type=str, required=True, help='Bedrock Knowledge Base ID')
    parser.add_argument('--llm-model', type=str, default='meta.llama3-8b-instruct-v1:0', help='Bedrock LLM Model ID')
    parser.add_argument('--embedding-model', type=str, default='amazon.titan-embed-text-v1', help='Bedrock Embedding Model ID')
    args = parser.parse_args()
    
    # Initialize the RAG system
    rag = BedrockRAG(
        kb_id=args.kb_id,
        llm_model_id=args.llm_model,
        embedding_model_id=args.embedding_model
    )
    
    # Process the query
    start_time = time.time()
    result = rag.answer_query(args.query)
    end_time = time.time()
    
    # Print response
    print("\n" + "="*80)
    print(f"QUERY: {result['query']}")
    print("="*80)
    print(f"RESPONSE:\n{result['response']}")
    print("="*80)
    
    # Print details about retrieved data
    print("RETRIEVED DOCUMENTS:")
    for i, doc in enumerate(result['retrieved_data']['documents'], 1):
        print(f"{i}. Title: {doc['metadata'].get('title', 'Untitled')} (Score: {doc['score']:.4f})")
    
    print("\nRETRIEVED IMAGES:")
    for i, img in enumerate(result['retrieved_data']['images'], 1):
        print(f"{i}. URL: {img['metadata'].get('image_url', '')} (Score: {img['score']:.4f})")
    
    print(f"\nTotal processing time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()