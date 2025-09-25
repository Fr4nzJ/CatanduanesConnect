from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
import logging
from chatbot import get_response, ERROR_PROCESSING, ERROR_EMPTY_INPUT
import torch

# Set up logging
logger = logging.getLogger(__name__)

bp = Blueprint('chatbot', __name__)

@bp.route('/chat')
def chat():
    """Render the chat interface."""
    return render_template('chat.html')

@bp.route('/chat', methods=['POST'])
def process_message():
    """Process chat messages and return responses using memory-optimized model."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            logger.error("Invalid request data")
            return jsonify({'error': ERROR_EMPTY_INPUT}), 400

        message = data['message'].strip()
        if not message:
            return jsonify({'error': ERROR_EMPTY_INPUT}), 400

        logger.info("Generating response...")
        with torch.inference_mode():  # Memory optimization
            response = get_response(message)

        if response in [ERROR_PROCESSING, ERROR_EMPTY_INPUT]:
            logger.error(f"Error generating response: {response}")
            return jsonify({'error': response}), 500

        result = {
            'response': response,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(result)

    except Exception as e:
        logger.exception("Error in chat processing")
        return jsonify({'error': ERROR_PROCESSING}), 500

# Remove unused routes since we're using chat bubble overlay