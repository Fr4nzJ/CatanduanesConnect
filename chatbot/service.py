"""
Chatbot service implementation using Hugging Face Inference API.
"""
import os
import logging
import requests
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Chatbot service using Hugging Face Inference API.
    """
    def __init__(self):
        self.model = "distilgpt2"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        
        # Error messages
        self.ERROR_NO_TOKEN = "⚠️ Hugging Face API token not configured."
        self.ERROR_API_GENERIC = "⚠️ I couldn't generate a reply."
        self.ERROR_MODEL_LOADING = "⚠️ Model is loading, please try again in a moment."
        self.ERROR_EMPTY_MESSAGE = "⚠️ Please provide a message."

    def query(self, payload: Dict[str, Any]) -> Optional[Dict]:
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
                self.api_url, 
                headers=headers, 
                json=payload,
                timeout=30  # 30 second timeout
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                logger.warning("Model is still loading")
                return {"error": self.ERROR_MODEL_LOADING}
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {"error": self.ERROR_API_GENERIC}
                
        except requests.Timeout:
            logger.error("Request timed out")
            return {"error": "⚠️ Request timed out. Please try again."}
        except Exception as e:
            logger.error(f"Error in query: {str(e)}")
            return {"error": self.ERROR_API_GENERIC}

    def chatbot_response(self, message: str) -> str:
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
            return self.ERROR_EMPTY_MESSAGE
            
        # Check for API token
        if not os.getenv("HF_API_KEY"):
            return self.ERROR_NO_TOKEN
            
        try:
            # Query the model
            result = self.query({"inputs": message})
            
            # Handle various response scenarios
            if result is None:
                return self.ERROR_API_GENERIC
                
            if "error" in result:
                return result["error"]
                
            # Handle different model response formats
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "generated_text" in result[0]:
                    text = result[0]["generated_text"].strip()
                    # Remove the input prompt from the response
                    return text[len(message):].strip() if text else self.ERROR_API_GENERIC
                elif isinstance(result[0], str):
                    text = result[0].strip()
                    # Remove the input prompt from the response
                    return text[len(message):].strip() if text else self.ERROR_API_GENERIC
                    
            logger.error(f"Unexpected API response format: {result}")
            return self.ERROR_API_GENERIC
            
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            return self.ERROR_API_GENERIC

# Create singleton instance
chatbot_service = ChatbotService()