import os
import logging
import requests
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL = "facebook/blenderbot-400M-distill"  # Default model
# Alternative models:
# MODEL = "distilgpt2"
# MODEL = "mistralai/Mistral-7B-Instruct"

# API configuration
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

# Error messages
ERROR_NO_TOKEN = "⚠️ Hugging Face API token not configured. Please contact the administrator."
ERROR_API_GENERIC = "⚠️ An error occurred while processing your request. Please try again later."
ERROR_MODEL_LOADING = "⚠️ The model is still loading. Please try again in a few moments."

def query(payload: Dict[str, Any]) -> Optional[Dict]:
    """
    Send a query to the Hugging Face Inference API.
    
    Args:
        payload (Dict[str, Any]): The request payload containing the input text
        
    Returns:
        Optional[Dict]: The API response or None if an error occurs
    """
    api_token = os.getenv("HF_API_KEY")
    if not api_token:
        logger.error("HF_API_KEY environment variable not set")
        return None
        
    headers = {"Authorization": f"Bearer {api_token}"}
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            logger.warning("Model is still loading")
            return {"error": ERROR_MODEL_LOADING}
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return {"error": f"⚠️ Error from Hugging Face: {response.text}"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {"error": ERROR_API_GENERIC}

def generate_reply(message: str) -> str:
    """
    Generate a chatbot reply using the Hugging Face Inference API.
    
    Args:
        message (str): The user's input message
        
    Returns:
        str: The model's response or an error message
    """
    if not message.strip():
        return "Please provide a message."
        
    # Check for API token
    if not os.getenv("HF_API_KEY"):
        return ERROR_NO_TOKEN
        
    try:
        # Query the model
        result = query({"inputs": message})
        
        # Handle various response scenarios
        if result is None:
            return ERROR_API_GENERIC
            
        if "error" in result:
            return result["error"]
            
        # Handle different model response formats
        if isinstance(result, list) and len(result) > 0:
            if isinstance(result[0], dict) and "generated_text" in result[0]:
                return result[0]["generated_text"]
            elif isinstance(result[0], str):
                return result[0]
                
        logger.error(f"Unexpected API response format: {result}")
        return ERROR_API_GENERIC
        
    except Exception as e:
        logger.error(f"Error generating reply: {str(e)}")
        return ERROR_API_GENERIC