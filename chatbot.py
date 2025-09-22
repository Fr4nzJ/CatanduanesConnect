"""
Chatbot implementation using Hugging Face Router API with OpenAI-compatible interface.
"""
import os
import logging
from typing import Optional
from openai import OpenAI

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = "google/gemma-2-2b-it:nebius"  # A good conversational model

# Initialize OpenAI client with Hugging Face router
client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.getenv("HF_TOKEN"),
)

# Error messages
ERROR_NO_TOKEN = "⚠️ API token not configured"
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_API_TIMEOUT = "⚠️ Request timed out, please try again"
ERROR_API_ERROR = "⚠️ Could not generate a response"
ERROR_MODEL_LOADING = "⚠️ Model is loading, please try again in a moment"

def get_response(prompt: str) -> str:
    """
    Generate a response using the Hugging Face Router API with OpenAI interface.
    """
    if not prompt or not prompt.strip():
        return ERROR_EMPTY_INPUT
    
    if not HF_TOKEN:
        return ERROR_NO_TOKEN

    try:
        # Create chat completion
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": prompt.strip()
                }
            ],
            temperature=0.7,  # Add some creativity
            max_tokens=150,   # Keep responses concise
            timeout=30        # Timeout in seconds
        )
        
        # Extract response
        if completion and completion.choices:
            return completion.choices[0].message.content.strip()
        return ERROR_API_ERROR

    except TimeoutError:
        logger.error("API request timed out")
        return ERROR_API_TIMEOUT
    except Exception as e:
        if "model is loading" in str(e).lower():
            logger.warning("Model is still loading")
            return ERROR_MODEL_LOADING
        logger.error(f"Error generating response: {str(e)}")
        return ERROR_API_ERROR
