import unittest
import os
from dotenv import load_dotenv
import google.generativeai as genai
from gemini_client import GeminiChat, reset_chat_instance

# Load environment variables
load_dotenv()

class TestGeminiChat(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.api_key = os.getenv("GEMINI_API_KEY")
        print("API Key:", "*" * (len(self.api_key) - 4) + self.api_key[-4:] if self.api_key else None)
        try:
            self.chat = GeminiChat(api_key=self.api_key)
            model = genai.GenerativeModel("gemini-pro")
            print("Available models:", [m.name for m in genai.list_models()])
        except Exception as e:
            print("Setup error:", str(e))
        
    def tearDown(self):
        """Clean up after tests."""
        reset_chat_instance()
        
    def test_basic_response(self):
        """Test basic message response."""
        message = "What is Catanduanes Connect?"
        response = self.chat.send_message(message)
        
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        self.assertIn("Catanduanes", response)
        
    def test_context_handling(self):
        """Test response with additional context."""
        message = "What services are available?"
        context = "There are currently 15 registered businesses offering various services including: restaurants, hotels, and transportation."
        response = self.chat.send_message(message, context=context)
        
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        self.assertTrue(
            any(word in response.lower() for word in ["restaurant", "hotel", "transportation"])
        )
        
    def test_conversation_history(self):
        """Test response with conversation history."""
        history = [
            {"role": "user", "content": "What is the weather like in Catanduanes?"},
            {"role": "assistant", "content": "I don't have access to real-time weather data. You should check a weather service for current conditions in Catanduanes."},
        ]
        message = "Why is that?"
        response = self.chat.send_message(message, history=history)
        
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
    def test_streaming_response(self):
        """Test streaming response functionality."""
        try:
            message = "Tell me about Catanduanes."
            chunks = []
            
            # Collect streaming response
            for chunk in self.chat.stream_message(message):
                self.assertIsInstance(chunk, str)
                chunks.append(chunk)
                
            # Verify we got some chunks
            self.assertTrue(len(chunks) > 0)
            
            # Verify combined response makes sense
            full_response = ''.join(chunks)
            self.assertTrue(len(full_response) > 0)
            if "quota exceeded" in full_response.lower() or "rate limit" in full_response.lower():
                self.skipTest("API rate limit exceeded")
            else:
                self.assertIn("Catanduanes", full_response)
        except Exception as e:
            if "quota exceeded" in str(e).lower() or "rate limit" in str(e).lower():
                self.skipTest("API rate limit exceeded")
            else:
                raise
        
    def test_error_handling(self):
        """Test error handling with invalid input."""
        # Test with None message
        with self.assertRaises(ValueError):
            self.chat.send_message(None)
            
        # Test with empty message
        with self.assertRaises(ValueError):
            self.chat.send_message("")
            
        with self.assertRaises(ValueError):
            self.chat.send_message("   ")
            
        # Test with invalid history format
        invalid_history = [{"invalid": "format"}]
        response = self.chat.send_message("test", history=invalid_history)
        self.assertTrue("trouble" in response.lower())

if __name__ == '__main__':
    unittest.main()