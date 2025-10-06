from flask import Blueprint, render_template, request, jsonify, current_app, session
from flask_login import login_required, current_user
from datetime import datetime
import logging
from typing import List, Dict, Optional

from gemini_client import get_chat_instance
from models import JobOffer, ServiceRequest, Business
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
                context_parts.append(f"  Type: {business.business_type}")
                if business.description:
                    context_parts.append(f"  Description: {business.description[:200]}...")
                    
        return "\n".join(context_parts) if context_parts else None
        
    except Exception as e:
        logger.error(f"Error retrieving relevant data: {str(e)}")
        return None

@bp.route('/chat')
@login_required
def chat():
    """Render the chat interface."""
    return render_template('chatbot/chat.html')

@bp.route('/api/chat', methods=['POST'])
@login_required
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
        
        # Get relevant data from Neo4j based on user query
        context = get_relevant_data(user_message)
        
        try:
            # Get Gemini chat instance and process message
            logger.info(f"Processing message with Gemini API: {user_message[:100]}...")
            gemini = get_chat_instance()
            if gemini is None:
                logger.error("Failed to get Gemini chat instance")
                return jsonify({
                    'status': 'error',
                    'error': ERROR_PROCESSING,
                    'message': 'Chatbot service is temporarily unavailable'
                }), 503

            response = gemini.process_message(
                message=user_message,
                history=chat_history,
                context=context
            )
            logger.info(f"Received Gemini response: {response[:100]}...")
                
        except Exception as e:
            logger.error(f"Gemini chat error: {str(e)}")
            return jsonify({
                'status': 'error',
                'error': ERROR_PROCESSING,
                'message': 'An error occurred while generating the response'
            }), 500
            
        # Update chat history
        chat_history.extend([
            {'role': 'user', 'content': user_message},
            {'role': 'assistant', 'content': response}
        ])
        
        # Keep only last 10 pairs (20 messages) to prevent session from growing too large
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
            
        # Save history to session
        session['chat_history'] = chat_history
        
        return jsonify({
            'status': 'success',
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': ERROR_PROCESSING,
            'message': 'An error occurred processing your request'
        }), 500

