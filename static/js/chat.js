document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chatContainer');
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('userMessage');

    // Add typing indicator styles
    const style = document.createElement('style');
    style.textContent = `
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 4px 8px;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            background: rgba(255, 255, 255, 0.6);
            border-radius: 50%;
            animation: typing 1s infinite ease-in-out;
        }
        
        .typing-indicator span:nth-child(1) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(2) { animation-delay: 0.3s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .message-bubble.error {
            background: rgba(220, 53, 69, 0.1);
            border-color: rgba(220, 53, 69, 0.3);
        }
        
        .message-bubble.thinking {
            background: rgba(255, 255, 255, 0.05);
        }
    `;
    document.head.appendChild(style);

    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Create user message bubble
        const userDiv = document.createElement('div');
        userDiv.className = 'message-bubble user fade-in';
        userDiv.textContent = message;
        chatContainer.appendChild(userDiv);
        
        // Clear input and disable
        messageInput.value = '';
        messageInput.disabled = true;
        messageInput.placeholder = 'Processing...';
        
        // Show thinking indicator
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message-bubble bot fade-in thinking';
        thinkingDiv.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        chatContainer.appendChild(thinkingDiv);
        
        // Scroll to bottom with smooth animation
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
        
        // Send request to server
        fetch('/chatbot/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            // Remove thinking indicator
            chatContainer.removeChild(thinkingDiv);
            
            // Create bot response bubble
            const botDiv = document.createElement('div');
            botDiv.className = 'message-bubble bot fade-in';
            
            if (data.error) {
                botDiv.innerHTML = `<i class="fas fa-exclamation-circle text-warning me-2"></i>${data.error}`;
            } else {
                botDiv.textContent = data.response;
            }
            
            chatContainer.appendChild(botDiv);
            
            // Smooth scroll to bottom
            chatContainer.scrollTo({
                top: chatContainer.scrollHeight,
                behavior: 'smooth'
            });
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Remove thinking indicator
            chatContainer.removeChild(thinkingDiv);
            
            // Show error message
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-bubble bot fade-in error';
            errorDiv.innerHTML = '<i class="fas fa-exclamation-triangle text-danger me-2"></i>Sorry, there was an error processing your request.';
            chatContainer.appendChild(errorDiv);
        })
        .finally(() => {
            // Re-enable input
            messageInput.disabled = false;
            messageInput.placeholder = 'Type your message here...';
            messageInput.focus();
        });
    });

    // Focus input on load
    messageInput.focus();
});