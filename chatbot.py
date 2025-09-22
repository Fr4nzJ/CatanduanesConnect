import os
import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

import openai
from neo4j import GraphDatabase, exceptions as neo4j_exceptions
from flask import jsonify
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI configuration
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

class ChatbotService:
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

    def generate_cypher_query(self, message: str) -> Optional[str]:
        """Use GPT to generate a Cypher query from a natural language message."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-mini",
                messages=[
                    {"role": "system", "content": "You are a Cypher query generator. Generate only MATCH...RETURN queries. Never use CREATE, DELETE, MERGE, SET, REMOVE, or DROP. If the user's request requires modification, respond with None."},
                    {"role": "user", "content": f"Generate a Cypher query for: {message}"}
                ],
                temperature=0
            )
            
            query = response.choices[0].message['content'].strip()
            return query if self.is_safe_query(query) else None

        except Exception as e:
            logger.error(f"Error generating Cypher query: {str(e)}")
            return None

    def format_db_results(self, results: List[Dict[str, Any]], original_question: str) -> str:
        """Use GPT to format database results into a natural response."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that converts database results into natural language responses."},
                    {"role": "user", "content": f"Question: {original_question}\nDatabase results: {results}\nPlease format this into a natural response."}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message['content']

        except Exception as e:
            logger.error(f"Error formatting results: {str(e)}")
            return "I found some information but had trouble formatting it. Please try asking in a different way."

    def get_chatbot_response(self, message: str) -> str:
        """Get a general chatbot response without database query."""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for Catanduanes Connect, a platform that connects businesses, job seekers, and service providers in Catanduanes. Be friendly and professional."},
                    {"role": "user", "content": message}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message['content']

        except Exception as e:
            logger.error(f"Error getting chatbot response: {str(e)}")
            return "I'm having trouble right now. Please try again later."

    def process_message(self, message: str) -> Dict:
        """Process chat messages and return responses."""
        try:
            if not message:
                return {'error': 'No message provided'}, 400

            message = message.strip()

            # First, try to generate a Cypher query
            cypher_query = self.generate_cypher_query(message)

            if cypher_query:
                # Query involves database data
                try:
                    with self.driver.session(database=DATABASE) as session:
                        results = session.run(cypher_query).data()
                        
                        if results:
                            # Format the results using GPT
                            response = self.format_db_results(results, message)
                        else:
                            response = "I couldn't find any data matching your request. Could you please try asking in a different way?"

                except Exception as e:
                    logger.error(f"Database query error: {str(e)}")
                    response = "I encountered an error while searching the database. Please try again."

            else:
                # General conversation
                response = self.get_chatbot_response(message)

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
chatbot_service = ChatbotService()