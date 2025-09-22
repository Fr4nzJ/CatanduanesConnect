"""
Chatbot implementation using direct connection to Mem0 AI API.
"""
import os
import logging
import requests
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
MEM0_API_URL = os.getenv("MEM0_API_URL", "https://mem0-chatbot-production.up.railway.app")  # Your Railway URL
MEM0_API_TOKEN = os.getenv("MEM0_API_TOKEN")  # Optional API token if you have one

# Ensure URL has https:// prefix
if MEM0_API_URL and not MEM0_API_URL.startswith(('http://', 'https://')):
    MEM0_API_URL = 'https://' + MEM0_API_URL

# Ensure URL has https:// prefix
if MEM0_API_URL and not MEM0_API_URL.startswith(('http://', 'https://')):
    MEM0_API_URL = 'https://' + MEM0_API_URL

# Error messages
ERROR_NO_SERVER = "⚠️ Mem0 AI server not configured"
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_API_TIMEOUT = "⚠️ Request timed out, please try again"
ERROR_API_ERROR = "⚠️ Could not generate a response"
ERROR_MODEL_LOADING = "⚠️ The model is still loading, please try again in a moment"

def get_response(prompt: str) -> str:
    """
    Generate a response using Mem0 AI API.
    """
    if not prompt or not prompt.strip():
        logger.warning("Empty prompt received")
        return ERROR_EMPTY_INPUT
    
    if not MEM0_API_URL:
        logger.error("MEM0_API_URL not configured")
        return ERROR_NO_SERVER

    logger.info(f"Sending request to Mem0 AI: {MEM0_API_URL}")
    try:
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        if MEM0_API_TOKEN:
            headers["Authorization"] = f"Bearer {MEM0_API_TOKEN}"

        # Prepare payload
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are the CatanduanesConnect Assistant, an AI helper for the CatanduanesConnect platform."
                },
                {
                    "role": "user",
                    "content": prompt.strip()
                }
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }

        # Make request to Mem0 API
        response = requests.post(
            f"{MEM0_API_URL.rstrip('/')}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        logger.info(f"Response status code: {response.status_code}")

        # Extract response content
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content.strip()
            if content:
                logger.info(f"Generated response: {content}")
                return content
            
            logger.error("Empty response content")
            return ERROR_API_ERROR
        
        logger.error("No choices in response")
        return ERROR_API_ERROR

    except TimeoutError:
        logger.error("API request timed out")
        return ERROR_API_TIMEOUT
    except ConnectionError as e:
        logger.error(f"Could not connect to Mem0 AI server: {e}")
        return "⚠️ Could not connect to AI server"
    except Exception as e:
        logger.exception("Unexpected error while processing response:")
        return ERROR_API_ERROR
