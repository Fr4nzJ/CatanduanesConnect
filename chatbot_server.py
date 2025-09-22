"""
FastAPI server for Hugging Face Transformers chatbot.
"""
import os
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import AutoModelForCausalLM, AutoTokenizer, TextGenerationPipeline, pipeline

# Create FastAPI app
app = FastAPI(title="Chatbot API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model configuration
MODEL_ID = "distilgpt2"
MAX_LENGTH = 150
NUM_SEQUENCES = 1
TEMPERATURE = 0.7

# Initialize model and tokenizer at startup
try:
    print("Loading model and tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID)
    text_generator = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    raise

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Generate a chat response using the loaded model.
    """
    # Input validation
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        # Generate response
        result = text_generator(
            request.message,
            max_length=MAX_LENGTH,
            num_return_sequences=NUM_SEQUENCES,
            do_sample=True,
            temperature=TEMPERATURE
        )

        if not result or len(result) == 0:
            raise HTTPException(status_code=500, detail="Failed to generate response")

        # Extract generated text, removing the input prompt
        generated = result[0]["generated_text"]
        response = generated[len(request.message):].strip()

        if not response:
            raise HTTPException(status_code=500, detail="Generated empty response")

        return ChatResponse(reply=response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("chatbot_server:app", host="0.0.0.0", port=port, reload=True)