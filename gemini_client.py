import os
import logging
import re
import time
from typing import List, Dict, Optional, Any, Iterator
from datetime import datetime
import google.generativeai as genai
from google.api_core import retry
from database_queries import search_businesses, search_jobs, search_services

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Rate limiting settings
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
MAX_RETRY_DELAY = 60.0

SYSTEM_TEMPLATE = """You are a helpful AI assistant for CatanduanesConnect, a platform connecting job seekers, 
businesses, and service providers in Catanduanes. Your role is to help users find jobs, businesses, and services, 
and answer their questions about the platform.

When users ask about:
1. Jobs - Search the database and provide relevant job listings
2. Businesses - Search the database and provide business information
3. Services - Search the database and provide available services

For any other questions, provide helpful general information about Catanduanes or the platform."""

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
            
    def extract_search_params(self, message: str) -> Dict[str, str]:
        """Extract search parameters from the user's message."""
        params = {}
        
        # Look for category in the message
        category_patterns = [
            r"category[:\s]+(\w+)",
            r"in the (\w+) category",
            r"related to (\w+)",
            r"about (\w+)"
        ]
        for pattern in category_patterns:
            match = re.search(pattern, message.lower())
            if match:
                params["category"] = match.group(1)
                break

        # Look for location in the message
        location_patterns = [
            r"in\s+(\w+(?:\s+\w+)*(?:\s+City)?)",
            r"at\s+(\w+(?:\s+\w+)*(?:\s+City)?)",
            r"near\s+(\w+(?:\s+\w+)*(?:\s+City)?)",
            r"around\s+(\w+(?:\s+\w+)*(?:\s+City)?)"
        ]
        for pattern in location_patterns:
            match = re.search(pattern, message)
            if match:
                params["location"] = match.group(1)
                break
                
        # Use the rest as a general search query
        # Remove found category and location if any
        query = message
        if "category" in params:
            query = re.sub(r"category[:\s]+" + params["category"], "", query, flags=re.IGNORECASE)
        if "location" in params:
            query = re.sub(r"in\s+" + params["location"], "", query, flags=re.IGNORECASE)
        
        query = query.strip()
        if query and not all(word in ["show", "find", "get", "list", "me", "please", "can", "you", "tell", "about"] for word in query.lower().split()):
            params["query"] = query
            
        return params

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
            
        # Check if the message is about jobs, businesses, or services
        message_lower = message.lower()
        search_params = self.extract_search_params(message)
        
        # Prepare database results if relevant
        db_results = []
        if any(word in message_lower for word in ["job", "work", "career", "position", "employment", "hiring"]):
            db_results = search_jobs(**search_params)
            if db_results:
                context = f"Here are some relevant jobs I found in our database:\n\n" + \
                         "\n\n".join([f"- {job.get('title', 'Untitled Position')}\n  " + \
                                    f"Description: {job.get('description', 'No description available')}\n  " + \
                                    f"Location: {job.get('location', 'Location not specified')}\n  " + \
                                    f"Category: {job.get('category', 'Category not specified')}" 
                                    for job in db_results])
                         
        elif any(word in message_lower for word in ["business", "company", "store", "shop"]):
            db_results = search_businesses(**search_params)
            if db_results:
                context = f"Here are some relevant businesses I found in our database:\n\n" + \
                         "\n\n".join([f"- {business.get('name', 'Unnamed Business')}\n  " + \
                                    f"Description: {business.get('description', 'No description available')}\n  " + \
                                    f"Location: {business.get('location', 'Location not specified')}\n  " + \
                                    f"Category: {business.get('category', 'Category not specified')}" 
                                    for business in db_results])
                         
        elif any(word in message_lower for word in ["service", "provider"]):
            db_results = search_services(**search_params)
            if db_results:
                context = f"Here are some relevant services I found in our database:\n\n" + \
                         "\n\n".join([f"- {service.get('name', 'Unnamed Service')}\n  " + \
                                    f"Description: {service.get('description', 'No description available')}\n  " + \
                                    f"Location: {service.get('location', 'Location not specified')}\n  " + \
                                    f"Category: {service.get('category', 'Category not specified')}" 
                                    for service in db_results])
        
        if db_results:
            message = f"{message}\n\nPlease provide a helpful response based on the database results I've provided."
            
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
            
            # Get model response with retries
            retry_count = 0
            last_error = None
            delay = INITIAL_RETRY_DELAY
            
            while retry_count < MAX_RETRIES:
                try:
                    model = genai.GenerativeModel(self.model)
                    chat = model.start_chat(
                        history=[
                            {"role": part["role"], "parts": part["parts"]}
                            for part in parts[:-1]
                        ] if len(parts) > 1 else None)
                    break
                except Exception as e:
                    if "429" in str(e):  # Rate limit error
                        retry_count += 1
                        if retry_count == MAX_RETRIES:
                            logger.error(f"Max retries ({MAX_RETRIES}) exceeded for rate limit")
                            return "I apologize, but I'm currently experiencing heavy traffic. Please try again in a minute."
                        
                        logger.warning(f"Rate limit hit, attempt {retry_count}/{MAX_RETRIES}. Waiting {delay}s")
                        time.sleep(delay)
                        delay = min(delay * 2, MAX_RETRY_DELAY)  # Exponential backoff
                        last_error = e
                        continue
                    else:
                        logger.error(f"Error creating chat: {str(e)}")
                        raise
            
            # Send message with retries
            retry_count = 0
            delay = INITIAL_RETRY_DELAY
            
            while retry_count < MAX_RETRIES:
                try:
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
                    if "429" in str(e):  # Rate limit error
                        retry_count += 1
                        if retry_count == MAX_RETRIES:
                            logger.error(f"Max retries ({MAX_RETRIES}) exceeded for rate limit")
                            return "I apologize, but I'm currently experiencing heavy traffic. Please try again in a minute."
                        
                        logger.warning(f"Rate limit hit, attempt {retry_count}/{MAX_RETRIES}. Waiting {delay}s")
                        time.sleep(delay)
                        delay = min(delay * 2, MAX_RETRY_DELAY)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Error sending message: {str(e)}")
                        return "I apologize, but I encountered an error processing your request. Please try again later."
            
        except Exception as e:
            logger.error(f"Error processing message with Gemini: {str(e)}")
            return "I apologize, but I encountered an unexpected error. Please try again later."
            
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