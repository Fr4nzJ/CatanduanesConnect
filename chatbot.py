"""
Chatbot implementation using direct connection to Mem0 AI on Railway.
"""
import os
import logging
import requests
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
MEM0_API_URL = os.getenv("MEM0_API_URL", "mem0-chatbot-production.up.railway.app")  # Your Railway URL
MEM0_API_TOKEN = os.getenv("MEM0_API_TOKEN")  # Optional API token if you have one

# Error messages
ERROR_NO_SERVER = "⚠️ Mem0 AI server not configured"
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_API_TIMEOUT = "⚠️ Request timed out, please try again"
ERROR_API_ERROR = "⚠️ Could not generate a response"
ERROR_MODEL_LOADING = "⚠️ The model is still loading, please try again in a moment"

def get_response(prompt: str) -> str:
    """
    Generate a response using Mem0 AI hosted on Railway.
    """
    if not prompt or not prompt.strip():
        return ERROR_EMPTY_INPUT
    
    if not MEM0_API_URL:
        return ERROR_NO_SERVER

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

        # Handle common status codes
        if response.status_code == 503:
            logger.warning("Mem0 AI is still loading")
            return ERROR_MODEL_LOADING
        elif response.status_code == 429:
            logger.warning("Rate limit exceeded")
            return "⚠️ Too many requests, please try again in a moment"

        response.raise_for_status()
        
        # Parse response
        result = response.json()
        if result and "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            content = message.get("content", "").strip()
            return content if content else ERROR_API_ERROR
        return ERROR_API_ERROR

    except requests.Timeout:
        logger.error("API request timed out")
        return ERROR_API_TIMEOUT
    except requests.ConnectionError:
        logger.error("Could not connect to Mem0 AI server")
        return "⚠️ Could not connect to AI server"
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return ERROR_API_ERROR
