from gemini_client import GeminiChat

def test_chat():
    # Initialize the chat client
    chat = GeminiChat()
    
    # Test a simple conversation
    response = chat.send_message(
        message="Hi! Can you tell me what CatanduanesConnect is?",
        history=[],
        context=""
    )
    
    print("Test response:", response)

if __name__ == "__main__":
    test_chat()