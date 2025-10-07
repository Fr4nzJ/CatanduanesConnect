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

        // Show thinking indicator
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message bot-message thinking';
        thinkingDiv.innerHTML = `
            <div class="message-content">
                <i class="fas fa-circle-notch fa-spin me-2"></i>Thinking...
            </div>
        `;
        thinkingDiv.id = 'thinking';
        this.messagesContainer.appendChild(thinkingDiv);
        this.scrollToBottom();

        try {
            // Send message to chatbot server using new Gemini endpoint
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({ message })
            });

            // Remove thinking indicator
            const thinking = document.getElementById('thinking');
            if (thinking) thinking.remove();

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || error.error || 'Failed to get response');
            }

            const data = await response.json();
            
            // Add bot response to chat
            if (data.status === 'success' && data.message) {
                this.addMessage(data.message, 'bot');
            } else if (data.error) {
                this.addMessage(`Sorry, an error occurred: ${data.message}`, 'bot');
            } else {
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            
            // Remove thinking indicator if still present
            const thinking = document.getElementById('thinking');
            if (thinking) thinking.remove();
        }

        // Scroll to bottom
        this.scrollToBottom();
    }

    addMessage(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        // Format message content with proper spacing and bullet points
        const formattedText = text
            .replace(/•/g, '<br>•')  // Add line breaks before bullet points
            .replace(/\n/g, '<br>')  // Convert newlines to <br>
            .trim();

        messageDiv.innerHTML = `
            <div class="message-content">
                ${formattedText}
            </div>
        `;
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