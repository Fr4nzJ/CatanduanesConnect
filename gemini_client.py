import os
import logging
from typing import List, Dict, Optional
import google.generativeai as genai
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class GeminiChat:
    """Client for interacting with Google's Gemini API."""
    
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Start a new chat
        self.chat = self.model.start_chat(history=[])
        
    def process_message(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[str] = None
    ) -> str:
        """
        Process a chat message with optional history and context.
        
        Args:
            message: The user's message
            history: Optional list of previous messages [{"role": "user|assistant", "content": "..."}]
            context: Optional context string (e.g., relevant business/job data)
            
        Returns:
            String containing the assistant's response
        """
        try:
            # Build the prompt
            prompt_parts = []
            
            # Add system context if provided
            if context:
                prompt_parts.append(f"""As an AI assistant for CatanduanesConnect, use this relevant information to help answer the query:

{context}

Remember to reference specific details from this context when appropriate in your response.""")
            
            # Add conversation history
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        prompt_parts.append(f"User: {msg['content']}")
                    else:
                        prompt_parts.append(f"Assistant: {msg['content']}")
            
            # Add the current message
            prompt_parts.append(f"User: {message}")
            
            # Get response from Gemini
            response = self.model.generate_content("\n".join(prompt_parts))
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            raise

# Create a singleton instance
try:
    gemini_chat = GeminiChat()
except Exception as e:
    logger.error(f"Failed to initialize Gemini chat: {str(e)}")
    gemini_chat = None

def get_chat_instance() -> GeminiChat:
    """
    Get or create a Gemini chat instance.
    
    Returns:
        GeminiChat instance
        
    Raises:
        RuntimeError if initialization fails
    """
    global gemini_chat
    
    if gemini_chat is None:
        try:
            gemini_chat = GeminiChat()
        except Exception as e:
            logger.error(f"Failed to create Gemini chat instance: {str(e)}")
            raise RuntimeError("Could not initialize Gemini chat")
            
    return gemini_chat