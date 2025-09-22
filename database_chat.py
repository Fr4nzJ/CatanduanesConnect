import os
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from neo4j import GraphDatabase, exceptions as neo4j_exceptions
from flask import jsonify
from dotenv import load_dotenv

from huggingface_chatbot import generate_reply

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

class DatabaseChatService:
    def __init__(self):
        if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
            logger.error("Missing required Neo4j environment variables!")
            raise ValueError("Missing required Neo4j environment variables!")

        # Neo4j driver setup
        try:
            self.driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
            )
            with self.driver.session(database=DATABASE) as session:
                result = session.run("RETURN 1")
                result.single()
            logger.info("Successfully connected to Neo4j database")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise

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
            response = generate_reply(message)

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