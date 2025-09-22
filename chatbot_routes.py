from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import logging
from chatbot import get_response  # Import the get_response function directly

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
        # Log request data
        data = request.get_json()
        logger.info(f"Received chat request: {data}")
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        if 'message' not in data:
            logger.error("No message field in request data")
            return jsonify({'error': 'No message provided'}), 400

        # Get response from chatbot
        message = data['message']
        logger.info(f"Sending message to chatbot: {message}")
        response = get_response(message)
        logger.info(f"Received response from chatbot: {response}")

        # Format response
        result = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)
    except Exception as e:
        logger.exception("Unexpected error in process_message:")
        return jsonify({
            'error': f'Error: {str(e)}'
        }), 500

# Remove unused routes since we're using chat bubble overlay