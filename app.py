import streamlit as st
import boto3
import json
import re
import time
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# Access AWS credentials from Streamlit Secrets
AWS_ACCESS_KEY_ID = st.secrets["Home_AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = st.secrets["Home_AWS_SECRET_ACCESS_KEY"]

# Configure page
st.set_page_config(
    page_title="Renesas Technical Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #34495e;
        margin-bottom: 1rem;
    }
    .response-box {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid #007bff;
    }
    .source-box {
        background-color: #f0f7ff;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #cce5ff;
    }
    .metadata {
        color: #6c757d;
        font-size: 0.85rem;
    }
    .highlight {
        background-color: #fff3cd;
        padding: 2px 5px;
        border-radius: 3px;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #6c757d;
    }
    .img-container {
        display: flex;
        justify-content: center;
        margin: 20px 0;
    }
    .metrics-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.renesas.com/sites/default/files/inline-images/logo.png", width=200)
    st.markdown("## Configuration")
    
    # AWS Configuration
    kb_id = st.text_input("Knowledge Base ID", value="PXQS78QKBV")
    llm_model = st.selectbox(
        "LLM Model",
        ["us.meta.llama3-2-11b-instruct-v1:0"]
    )
    embedding_model = "amazon.titan-embed-text-v1"
    region = st.text_input("AWS Region", value="us-east-1")
    
    # Query settings
    top_k = st.slider("Maximum Results", min_value=1, max_value=10, value=5)
    score_threshold = st.slider("Minimum Score", min_value=0.1, max_value=1.0, value=0.6, step=0.05)
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        max_tokens = st.slider("Max Response Tokens", min_value=50, max_value=500, value=150)
        temperature = st.slider("Temperature", min_value=0.01, max_value=1.0, value=0.1, step=0.01)
        top_p = st.slider("Top P", min_value=0.1, max_value=1.0, value=0.2, step=0.1)

# Main content
st.markdown("<h1 class='main-header'>Renesas Technical Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p>Ask any technical question about Renesas products and documentation</p>", unsafe_allow_html=True)

# Initialize clients
@st.cache_resource
def get_bedrock_clients():
    bedrock_runtime = boto3.client(
        'bedrock-runtime',
        region_name=region,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    bedrock_agent = boto3.client(
        'bedrock-agent-runtime',
        region_name=region,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )
    
    return bedrock_runtime, bedrock_agent

bedrock_runtime, bedrock_agent = get_bedrock_clients()

# RAG functions
def retrieve_from_kb(query, top_k=5, score_threshold=0.6):
    """Retrieve relevant content from Knowledge Base based on query."""
    try:
        with st.spinner("Retrieving information..."):
            # Retrieval using text query
            response = bedrock_agent.retrieve(
                knowledgeBaseId=kb_id,
                retrievalQuery={
                    "text": query
                },
                retrievalConfiguration={
                    "vectorSearchConfiguration": {
                        "numberOfResults": top_k
                    }
                }
            )
            
            # Process retrieved results
            retrieved_results = response.get("retrievalResults", [])
            
            # Filter by score threshold and sort by relevance
            filtered_results = []
            for result in retrieved_results:
                # Extract content and metadata
                content = result.get("content", {}).get("text", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0)
                
                # Skip if score is below threshold
                if score < score_threshold:
                    continue
                
                filtered_results.append({
                    "content": content,
                    "metadata": metadata,
                    "score": score
                })
            
            # Sort by score
            filtered_results = sorted(filtered_results, key=lambda x: x["score"], reverse=True)
            
            return {
                "results": filtered_results
            }
    except Exception as e:
        st.error(f"Error retrieving from Knowledge Base: {str(e)}")
        return {"results": []}

def generate_llm_response(query, retrieved_data):
    """Generate response using Bedrock LLM with retrieved data."""
    try:
        with st.spinner("Generating response..."):
            # Create context from retrieved data
            context = "I'm providing you with relevant information to answer the query.\n\n"
            
            # Add information from all results
            if retrieved_data["results"]:
                context += "RELEVANT INFORMATION:\n"
                for i, result in enumerate(retrieved_data["results"], 1):
                    context += f"Source {i}:\n"
                    if "title" in result["metadata"]:
                        context += f"Title: {result['metadata'].get('title', 'Untitled')}\n"
                    context += f"Content: {result['content']}\n\n"
            
            # Create prompt for LLM with very specific instructions
            prompt = f"""
Context:
{context}

User Query: {query}

IMPORTANT INSTRUCTIONS FOR RESPONSE:
1. Answer the query in 2-4 sentences maximum.
2. Include only essential information directly related to the query.
3. Do not repeat any information.
4. Do not use any formatting like tables, bullets, or separator lines.
5. Do not include any disclaimers, follow-ups, or offers of additional help.
6. Provide just the direct answer to the query and nothing more.

Answer:
"""
            # Call Bedrock LLM model
            request_body = json.dumps({
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature,
                "top_p": top_p
            })
            
            # Invoke the model
            response = bedrock_runtime.invoke_model(
                modelId=llm_model,
                body=request_body
            )
            
            # Parse the response
            response_body = json.loads(response.get('body').read())
            llm_response = response_body.get('generation', '')
            
            # Clean up the response
            # 1. Remove table formatting
            llm_response = llm_response.split('|')[0]
            llm_response = llm_response.replace('---', '')
            
            # 2. Remove repetitive sentences by splitting into sentences and removing duplicates
            sentences = [s.strip() for s in re.split(r'[.!?]+', llm_response) if s.strip()]
            unique_sentences = []
            for sentence in sentences:
                if sentence not in unique_sentences:
                    unique_sentences.append(sentence)
            
            # 3. Reconstruct the response with only unique sentences
            cleaned_response = '. '.join(unique_sentences[:4])  # Limit to 4 sentences
            if cleaned_response and not cleaned_response.endswith(('.', '!', '?')):
                cleaned_response += '.'
            
            return cleaned_response
    except Exception as e:
        st.error(f"Error generating LLM response: {str(e)}")
        return f"I'm sorry, I couldn't generate a response due to an error: {str(e)}"

def answer_query(query):
    """End-to-end function to answer a user query using RAG."""
    start_time = time.time()
    
    # Step 1: Retrieve relevant information from Knowledge Base
    retrieved_data = retrieve_from_kb(query, top_k, score_threshold)
    retrieval_time = time.time() - start_time
    
    # Step 2: Generate response using LLM
    response = generate_llm_response(query, retrieved_data)
    total_time = time.time() - start_time
    
    # Return response with retrieved data and timing information
    return {
        "query": query,
        "response": response,
        "retrieved_data": retrieved_data,
        "retrieval_time": retrieval_time,
        "total_time": total_time
    }

# Display image function
def display_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except:
        st.warning(f"Could not load image from URL: {url}")
        return None

# Query input
query = st.text_input("Ask your question", placeholder="How do I find RH850 device file?")

# Search button
if st.button("Search", type="primary") or query:
    if query:
        # Run the query
        result = answer_query(query)
        
        # Display timing metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Retrieval Time", f"{result['retrieval_time']:.2f}s")
        with col2:
            st.metric("Total Time", f"{result['total_time']:.2f}s")
        
        # Display the response
        st.markdown("<div class='response-box'>", unsafe_allow_html=True)
        st.markdown(f"<h2 class='sub-header'>Answer</h2>", unsafe_allow_html=True)
        st.markdown(f"{result['response']}", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Display sources
        with st.expander("View Sources", expanded=False):
            for i, source in enumerate(result['retrieved_data']['results'], 1):
                st.markdown(f"<div class='source-box'>", unsafe_allow_html=True)
                st.markdown(f"<h4>Source {i} (Score: {source['score']:.4f})</h4>", unsafe_allow_html=True)
                
                # Try to get title
                title = source['metadata'].get('title', 'Untitled')
                if title:
                    st.markdown(f"<b>Title:</b> {title}", unsafe_allow_html=True)
                
                # Display content
                st.markdown(f"<b>Content:</b> {source['content']}", unsafe_allow_html=True)
                
                # Try to display URL
                url = source['metadata'].get('url', source['metadata'].get('image_url', source['metadata'].get('s3_url', None)))
                if url:
                    st.markdown(f"<b>URL:</b> <a href='{url}' target='_blank'>{url}</a>", unsafe_allow_html=True)
                    
                    # If it looks like an image URL, try to display it
                    if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                        img = display_image(url)
                        if img:
                            st.image(img, caption=f"Source {i} Image", width=400)
                
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Please enter a question to search")

# Footer
st.markdown("<div class='footer'>Powered by Amazon Bedrock and Renesas Knowledge Base</div>", unsafe_allow_html=True)