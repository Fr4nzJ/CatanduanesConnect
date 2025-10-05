from flask import Blueprint, render_template, request, jsonify, current_app
from datetime import datetime
import logging

# Lazy import model-heavy libraries to avoid breaking app startup when optional
# dependencies (like torch) aren't installed in lightweight environments.
try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    torch = None
    TORCH_AVAILABLE = False

# chatbot module may import heavy ML libs; import it lazily inside the route
try:
    # attempt a light import to get error constants if available
    from chatbot import ERROR_PROCESSING, ERROR_EMPTY_INPUT
except Exception:
    ERROR_PROCESSING = 'error_processing'
    ERROR_EMPTY_INPUT = 'error_empty_input'

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
        # Ensure chatbot functionality is available
        if not TORCH_AVAILABLE:
            logger.warning('Torch not available; chatbot functionality is disabled')
            return jsonify({'error': 'chatbot_unavailable'}), 503

        try:
            # Lazy import to avoid import-time dependency on heavy modules
            from chatbot import get_response

            # Use torch.inference_mode if available
            if hasattr(torch, 'inference_mode'):
                with torch.inference_mode():
                    response = get_response(message)
            else:
                response = get_response(message)
        except Exception:
            logger.exception("Error generating response")
            return jsonify({'error': ERROR_PROCESSING}), 500

        if response in [ERROR_PROCESSING, ERROR_EMPTY_INPUT]:
            logger.error(f"Error generating response: {response}")
            return jsonify({'error': response}), 500

        result = {
            'reply': response,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(result)

    except Exception as e:
        logger.exception("Error in chat processing")
        return jsonify({'error': ERROR_PROCESSING}), 500

# Remove unused routes since we're using chat bubble overlay