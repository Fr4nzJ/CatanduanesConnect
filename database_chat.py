import os
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from dotenv import load_dotenv
from database import driver, DATABASE, get_neo4j_driver

# Ensure we have a driver
if driver is None:
    driver = get_neo4j_driver()
from flask import jsonify
from chatbot import get_response

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

class DatabaseChatService:
    def __init__(self):
        try:
            self.driver = get_neo4j_driver()
            self.database = get_database_name()
        except Exception as e:
            logger.error('Could not initialize Neo4j driver for chat service: %s', str(e), exc_info=True)
            self.driver = None
            self.database = os.getenv('NEO4J_DATABASE', 'neo4j')

    def is_safe_query(self, query: str) -> bool:
        """Check if a Cypher query is safe to execute."""
        dangerous_keywords = [
            r"\bDELETE\b",
            r"\bCREATE\b",
            r"\bMERGE\b",
            r"\bSET\b",
            r"\bREMOVE\b",
            r"\bDROP\b"
        ]
        
        query = query.upper()
        return all(not re.search(keyword, query) for keyword in dangerous_keywords)

    def process_message(self, message: str) -> Dict:
        """Process chat messages and return responses."""
        try:
            if not message:
                return {'error': 'No message provided'}, 400

            message = message.strip()

            # For now, we'll just use the Hugging Face chatbot
            # In the future, we can implement Neo4j queries here
            response = get_response(message)

            return {
                'response': response,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Chat processing error: {str(e)}")
            return {
                'error': 'Something went wrong. Please try again later.'
            }

# Create a singleton instance
database_chat_service = DatabaseChatService()