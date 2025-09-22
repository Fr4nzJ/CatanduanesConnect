from flask import Blueprint, render_template, request, jsonify
from .chatbot import chatbot_service

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

        result = chatbot_service.process_message(data['message'])
        
        if 'error' in result:
            return jsonify(result), 500
            
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'error': 'Something went wrong. Please try again later.'
        }), 500

@bp.route('/')
def chatbot_main():
    """Render the main chatbot page."""
    return render_template('chatbot/main.html')

@bp.route('/ai')
def chatbot_ai():
    """Render the AI chatbot page."""
    return render_template('chatbot/ai.html')

@bp.route('/support')
def chatbot_support():
    """Render the support chatbot page."""
    return render_template('chatbot/support.html')