from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import logging
from chatbot import chatbot_service  # Import from the chatbot package

# Set up logging
logger = logging.getLogger(__name__)

bp = Blueprint('chatbot', __name__)

@bp.route('/chat')
def chat():
    """Render the chat interface."""
    return render_template('chat.html')

@bp.route('/chat', methods=['POST'])
def process_message():
    """Process chat messages and return responses."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        response = chatbot_service.chatbot_response(data['message'])
        result = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'error': 'Something went wrong. Please try again later.'
        }), 500

# Remove unused routes since we're using chat bubble overlay