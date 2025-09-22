import os
import logging
import requests
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL = "distilgpt2"  # Fast and efficient text generation model

# API URL construction
API_URL = f"https://api-inference.huggingface.co/models/{MODEL}"

# Error messages
ERROR_NO_TOKEN = "⚠️ Hugging Face API token not configured."
ERROR_API_GENERIC = "⚠️ I couldn't generate a reply."
ERROR_MODEL_LOADING = "⚠️ Model is loading, please try again in a moment."
ERROR_EMPTY_MESSAGE = "⚠️ Please provide a message."

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
        response = requests.post(
            API_URL, 
            headers=headers, 
            json=payload,
            timeout=30  # 30 second timeout for slower models
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 503:
            logger.warning("Model is still loading")
            return {"error": ERROR_MODEL_LOADING}
        else:
            logger.error(f"API request failed with status {response.status_code}: {response.text}")
            return {"error": ERROR_API_GENERIC}
            
    except requests.Timeout:
        logger.error("Request timed out")
        return {"error": "⚠️ Request timed out. Please try again."}
    except requests.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {"error": ERROR_API_GENERIC}
    except Exception as e:
        logger.error(f"Unexpected error in query: {str(e)}")
        return {"error": ERROR_API_GENERIC}

def generate_reply(message: str) -> str:
    """
    Generate a chatbot reply using the Hugging Face Inference API.
    
    Args:
        message (str): The user's input message
        
    Returns:
        str: The model's response or an error message
    """
    # Input validation
    message = message.strip() if message else ""
    if not message:
        return ERROR_EMPTY_MESSAGE
        
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
                text = result[0]["generated_text"].strip()
                return text if text else ERROR_API_GENERIC
            elif isinstance(result[0], str):
                text = result[0].strip()
                return text if text else ERROR_API_GENERIC
                
        logger.error(f"Unexpected API response format: {result}")
        return ERROR_API_GENERIC
        
    except Exception as e:
        logger.error(f"Error generating reply: {str(e)}")
        return ERROR_API_GENERIC