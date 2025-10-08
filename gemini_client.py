import os
import logging
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime
import google.generativeai as genai

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are a helpful AI assistant for CatanduanesConnect, a platform connecting job seekers, 
businesses, and service providers in Catanduanes. Your role is to help users find jobs, businesses, and services, 
and answer their questions about the platform."""

class GeminiChat:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini client.
        
        Args:
            api_key: Google Gemini API key. If None, will try to get from environment.
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        try:
            # Initialize the Gemini client
            logger.debug("Initializing Gemini client...")
            
            genai.configure(api_key=api_key)
            self.model = "models/gemini-pro-latest"
            
            logger.info("Successfully initialized Gemini client")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise
            
    def send_message(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Send a message to the Gemini model.
        
        Args:
            message: The user's message
            history: Optional list of previous messages [{"role": "user|assistant", "content": "..."}]
            context: Optional context string (e.g., relevant business/job data)
            
        Returns:
            String containing the assistant's response
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
            
        try:
            # Build chat history as list of parts
            parts = []
            
            # Add system context if provided
            if context:
                parts.append({
                    "role": "user",
                    "parts": [{"text": SYSTEM_TEMPLATE + "\n" + context}]
                })
            
            # Add message history
            if history:
                for msg in history:
                    role = "model" if msg["role"] == "assistant" else "user"
                    parts.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })
            
            # Add current message
            parts.append({
                "role": "user",
                "parts": [{"text": message}]
            })
            
            # Get model response
            model = genai.GenerativeModel(self.model)
            chat = model.start_chat(
                history=[
                    {"role": part["role"], "parts": part["parts"]}
                    for part in parts[:-1]
                ] if len(parts) > 1 else None
            )
            
            response = chat.send_message(
                parts[-1]["parts"][0]["text"],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    candidate_count=1,
                    max_output_tokens=2048,
                    top_p=0.95,
                    top_k=40,
                )
            )
            
            # Extract and clean response
            if not response.text:
                raise ValueError("No response generated")
                
            text = response.text.strip()
            return text
            
        except Exception as e:
            logger.error(f"Error processing message with Gemini: {str(e)}")
            return "I apologize, but I'm having trouble processing your message. Please try again."
            
    def stream_message(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> Iterator[str]:
        """
        Send a message to the Gemini model and stream the response.
        
        Args:
            message: The user's message
            history: Optional list of previous messages [{"role": "user|assistant", "content": "..."}]
            context: Optional context string (e.g., relevant business/job data)
            
        Yields:
            Chunks of the assistant's response as they are generated
        """
        if not message or not message.strip():
            raise ValueError("Message cannot be empty")
            
        try:
            # Build chat history as list of parts
            parts = []
            
            # Add system context if provided
            if context:
                parts.append({
                    "role": "user",
                    "parts": [{"text": SYSTEM_TEMPLATE + "\n" + context}]
                })
            
            # Add message history
            if history:
                for msg in history:
                    role = "model" if msg["role"] == "assistant" else "user"
                    parts.append({
                        "role": role,
                        "parts": [{"text": msg["content"]}]
                    })
            
            # Add current message
            parts.append({
                "role": "user",
                "parts": [{"text": message}]
            })
            
            # Get model response stream
            model = genai.GenerativeModel(self.model)
            chat = model.start_chat(
                history=[
                    {"role": part["role"], "parts": part["parts"]}
                    for part in parts[:-1]
                ] if len(parts) > 1 else None
            )
            
            response_stream = chat.send_message(
                parts[-1]["parts"][0]["text"],
                stream=True,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    candidate_count=1,
                    max_output_tokens=2048,
                    top_p=0.95,
                    top_k=40,
                )
            )
            
            # Yield chunks as they arrive
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
            
        except Exception as e:
            logger.error(f"Error streaming message with Gemini: {str(e)}")
            yield "I apologize, but I'm having trouble processing your message. Please try again."


# Global instance for easy access
_chat_instance = None


def get_chat_instance() -> 'GeminiChat':
    """Get the global chat instance, creating it if necessary."""
    global _chat_instance
    if _chat_instance is None:
        _chat_instance = GeminiChat()
    return _chat_instance


def reset_chat_instance():
    """Reset the global chat instance (useful for testing)."""
    global _chat_instance
    _chat_instance = None