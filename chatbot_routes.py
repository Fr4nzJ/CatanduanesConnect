from flask import Blueprint, render_template, request, jsonify, current_app, session
from flask_login import login_required, current_user
from datetime import datetime
import logging
import os
from typing import List, Dict, Optional
from gemini_client import GeminiChat

# System prompt for CatanduanesConnect context
SYSTEM_PROMPT = """You are an AI assistant for CatanduanesConnect, a platform connecting job seekers, businesses, 
and service providers in Catanduanes. Help users find jobs, businesses, and services while providing accurate,
helpful information about opportunities in the region. When discussing jobs or services, always try to include
specific details about location, requirements, and how to apply or contact.

Key Features to Remember:
• Job searching and application assistance
• Business directory and service provider lookup
• Location-based recommendations
• Professional communication tips

Please maintain a helpful, professional tone and prioritize local opportunities in Catanduanes."""

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Gemini chat client
try:
    logger.info("Initializing Gemini chat client...")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    chatbot = GeminiChat(api_key=api_key)
    # Test the client with a simple message to verify it's working
    test_response = chatbot.send_message("test", context="Testing connection", history=[])
    if test_response:
        logger.info("Successfully initialized and tested Gemini chat client")
    else:
        raise ValueError("Failed to get response from Gemini chat client")
except Exception as e:
    logger.error(f"Failed to initialize Gemini chat client: {str(e)}", exc_info=True)
    chatbot = None
from models.search_methods import JobOffer, ServiceRequest, Business
from database import get_neo4j_driver

# Set up logging
logger = logging.getLogger(__name__)

# Error constants
ERROR_PROCESSING = 'error_processing'
ERROR_EMPTY_INPUT = 'error_empty_input'
ERROR_UNAUTHORIZED = 'error_unauthorized'

bp = Blueprint('chatbot', __name__)

def get_relevant_data(query: str) -> Optional[str]:
    """
    Retrieve relevant data from Neo4j based on user query.
    Returns formatted context string or None if no relevant data found.
    """
    try:
        context_parts = []
        
        # Search for relevant jobs
        jobs = JobOffer.search_by_keywords(query)
        if jobs:
            context_parts.append("Relevant Jobs:")
            for job in jobs[:3]:  # Limit to top 3 matches
                context_parts.append(f"- {job.title} at {job.company_name}")
                context_parts.append(f"  Location: {job.location}")
                context_parts.append(f"  Salary: ₱{job.salary}")
                context_parts.append(f"  Description: {job.description[:200]}...")
                
        # Search for relevant services
        services = ServiceRequest.search_by_keywords(query)
        if services:
            context_parts.append("\nRelevant Services:")
            for service in services[:3]:
                context_parts.append(f"- {service.title}")
                context_parts.append(f"  Location: {service.location}")
                context_parts.append(f"  Payment: ₱{service.payment_offer}")
                context_parts.append(f"  Description: {service.description[:200]}...")
                
        # Search for relevant businesses
        businesses = Business.search_by_keywords(query)
        if businesses:
            context_parts.append("\nRelevant Businesses:")
            for business in businesses[:3]:
                context_parts.append(f"- {business.name}")
                context_parts.append(f"  Location: {business.location}")
                context_parts.append(f"  Category: {business.category}")
                if business.description:
                    context_parts.append(f"  Description: {business.description[:200]}...")
                    
        return "\n".join(context_parts) if context_parts else None
        
    except Exception as e:
        logger.error(f"Error retrieving relevant data: {str(e)}")
        return None


@bp.route('/chat')
def chat():
    """Render the chat interface."""
    return render_template('chatbot/chat.html')

@bp.route('/api/chat', methods=['POST'])
def chat_api():
    """
    Handle chat API requests.

    Expects JSON: {
        "message": "user message"
    }
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'error': ERROR_EMPTY_INPUT,
                'message': 'No message provided'
            }), 400

        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'status': 'error',
                'error': ERROR_EMPTY_INPUT,
                'message': 'Message cannot be empty'
            }), 400

        # Get chat history from session
        chat_history = session.get('chat_history', [])

        # Get relevant context from database
        context = get_relevant_data(user_message)

        # Check if Gemini is initialized
        if chatbot is None:
            return jsonify({
                'status': 'error',
                'error': ERROR_PROCESSING,
                'message': 'Chatbot service is not available'
            }), 503

        try:
            # Format the context
            formatted_context = context if context else "No specific context available."
            
            # Send the message with context and get response
            response = chatbot.send_message(
                message=user_message,
                context=formatted_context,
                history=chat_history
            )

            # Format response
            formatted_response = response.strip()
            formatted_response = formatted_response.replace("**", "").replace("*", "• ")

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': ERROR_PROCESSING,
                'message': 'Error while generating response'
            }), 500

        # Update chat history in session
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": formatted_response})

        # Keep only the last 10 messages
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

        session['chat_history'] = chat_history

        # Return successful response
        return jsonify({
            'status': 'success',
            'message': formatted_response,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': ERROR_PROCESSING,
            'message': 'An error occurred while processing your message'
        }), 500


@bp.route('/api/chat/history', methods=['GET'])
@login_required
def get_chat_history():
    """Get the current user's chat history."""
    try:
        chat_history = session.get('chat_history', [])
        return jsonify({
            'status': 'success',
            'history': chat_history
        })
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': ERROR_PROCESSING,
            'message': 'Could not retrieve chat history'
        }), 500

@bp.route('/api/chat/clear', methods=['POST'])
@login_required
def clear_chat_history():
    """Clear the current user's chat history."""
    try:
        session['chat_history'] = []
        return jsonify({
            'status': 'success',
            'message': 'Chat history cleared'
        })
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': ERROR_PROCESSING,
            'message': 'Could not clear chat history'
        }), 500