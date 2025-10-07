import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

# Set up logging
logger = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are a helpful AI assistant for CatanduanesConnect, a platform connecting job seekers, 
businesses, and service providers in Catanduanes. Your role is to help users find jobs, businesses, and services, 
and answer their questions about the platform.

Context from the platform:
{context}

Conversation History:
{history}

Current User Message: {input}

Please provide a helpful and accurate response based on the context and conversation history."""

class GeminiChat:
    """Client for interacting with Google's Gemini API using LangChain."""
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Gemini chat client.
        
        Args:
            api_key: Google Gemini API key. If None, will try to get from environment.
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
            
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY environment variable is not set")
            
        try:
            # Initialize the LangChain Gemini chat model
            logger.debug("Initializing Gemini model with LangChain...")
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                temperature=0.7,
                google_api_key=api_key,
                convert_system_message_to_human=True
            )
            
            # Initialize conversation memory
            self.memory = ConversationBufferMemory(
                memory_key="history",
                input_key="input",
                output_key="response"
            )
            
            # Create prompt template
            self.prompt = PromptTemplate(
                input_variables=["context", "history", "input"],
                template=SYSTEM_TEMPLATE
            )
            
            # Create conversation chain
            self.chain = ConversationChain(
                llm=self.llm,
                memory=self.memory,
                prompt=self.prompt,
                verbose=False  # Set to True for debugging
            )
            
            logger.info("Successfully initialized Gemini chat with LangChain")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini API: {str(e)}")
            raise

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
            # Clear previous conversation memory
            self.memory.clear()
            
            # Add history to memory if provided
            if history:
                for msg in history:
                    if msg["role"] == "user":
                        self.memory.chat_memory.add_user_message(msg["content"])
                    else:
                        self.memory.chat_memory.add_ai_message(msg["content"])
            
            # Prepare context string
            context_str = context if context else "No additional context available."
            
            # Process the message through the chain
            response = self.chain.predict(
                context=context_str,
                history="",  # Memory will handle this
                input=message
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error processing message with Gemini: {str(e)}")
            return "I apologize, but I'm having trouble processing your message. Please try again."

# Global instance for easy access
_chat_instance = None

def get_chat_instance() -> GeminiChat:
    """Get the global chat instance, creating it if necessary."""
    global _chat_instance
    if _chat_instance is None:
        _chat_instance = GeminiChat()
    return _chat_instance

def reset_chat_instance():
    """Reset the global chat instance (useful for testing)."""
    global _chat_instance
    _chat_instance = None