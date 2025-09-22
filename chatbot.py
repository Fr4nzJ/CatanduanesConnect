"""
Chatbot implementation using Mem0 AI Python client.
"""
import os
import logging
from mem0 import MemoryClient
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Mem0 client
MEM0_API_KEY = os.getenv("MEM0_API_TOKEN")  # Get API key from environment
client = MemoryClient(api_key=MEM0_API_KEY)
import os
import logging
import requests
from typing import Optional
from mem0 import MemoryClient

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
MEM0_API_URL = os.getenv("MEM0_API_URL", "https://mem0-chatbot-production.up.railway.app")  # Your Railway URL
MEM0_API_TOKEN = os.getenv("MEM0_API_TOKEN")  # Optional API token if you have one

# Ensure URL has https:// prefix
if MEM0_API_URL and not MEM0_API_URL.startswith(('http://', 'https://')):
    MEM0_API_URL = 'https://' + MEM0_API_URL

# Error messages
ERROR_NO_API_KEY = "⚠️ Mem0 AI API key not configured"
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_API_TIMEOUT = "⚠️ Request timed out, please try again"
ERROR_API_ERROR = "⚠️ Could not generate a response"
ERROR_MODEL_LOADING = "⚠️ The model is still loading, please try again in a moment"

def get_response(prompt: str) -> str:
    """
    Generate a response using Mem0 AI client.
    """
    if not prompt or not prompt.strip():
        logger.warning("Empty prompt received")
        return ERROR_EMPTY_INPUT
    
    if not MEM0_API_KEY:
        logger.error("MEM0_API_KEY not configured")
        return ERROR_NO_API_KEY

    logger.info("Sending request to Mem0 AI")
    try:
        # Prepare messages
        messages = [
            {
                "role": "system",
                "content": "You are the CatanduanesConnect Assistant, an AI helper for the CatanduanesConnect platform."
            },
            {
                "role": "user",
                "content": prompt.strip()
            }
        ]
        logger.info(f"Request messages: {messages}")

        # Make request using Mem0 client
        response = client.chat.completions.create(
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        logger.info("Received response from Mem0 AI")

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
