// Chat Bubble functionality
class ChatBubble {
    constructor() {
        this.container = document.getElementById('chat-bubble-container');
        this.toggleButton = document.getElementById('chat-bubble-toggle');
        this.chatWindow = document.getElementById('chat-window');
        this.messagesContainer = document.getElementById('chat-messages');
        this.chatForm = document.getElementById('chat-form');
        this.chatInput = document.getElementById('chat-input');
        this.closeButton = document.querySelector('.close-chat');
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Toggle chat window
        this.toggleButton.addEventListener('click', () => this.toggleChat());
        this.closeButton.addEventListener('click', () => this.closeChat());

        // Handle message submission
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Handle input keypress (Enter to send)
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.handleSubmit(e);
            }
        });
    }

    toggleChat() {
        this.chatWindow.classList.toggle('hidden');
        if (!this.chatWindow.classList.contains('hidden')) {
            this.chatInput.focus();
        }
    }

    closeChat() {
        this.chatWindow.classList.add('hidden');
    }

    async handleSubmit(e) {
        e.preventDefault();
        const message = this.chatInput.value.trim();
        if (!message) return;

        // Clear input
        this.chatInput.value = '';

        // Add user message to chat
        this.addMessage(message, 'user');

        try {
            // Send message to chatbot server
            const response = await fetch('/chatbot/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to get response');
            }

            const data = await response.json();
            
            // Add bot response to chat
            if (data.reply) {
                this.addMessage(data.reply, 'bot');
            } else {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }

        // Scroll to bottom
        this.scrollToBottom();
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', `${type}-message`);
        messageDiv.textContent = text;
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// Initialize chat bubble when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ChatBubble();
});