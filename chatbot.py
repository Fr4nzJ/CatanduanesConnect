"""
Memory-optimized chatbot implementing Hugging Face transformers.
Uses 8-bit quantization to reduce memory usage for Railway deployment.
"""
import os
import logging
import torch
from typing import Optional
from transformers import AutoModelForSeq2SeqGeneration, AutoTokenizer
import bitsandbytes as bnb
from accelerate import init_empty_weights

# Set up logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "google/flan-t5-small"
MAX_LENGTH = 128
TEMPERATURE = 0.7

# Initialize model with 8-bit quantization
logger.info(f"Loading model {MODEL_NAME} in 8-bit mode...")

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir="models")

# Load model in 8-bit mode
model = AutoModelForSeq2SeqGeneration.from_pretrained(
    MODEL_NAME,
    load_in_8bit=True,
    device_map="auto",
    cache_dir="models"  # Cache locally to avoid redownloading
)

# Error messages
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_PROCESSING = "⚠️ Error processing your request"
ERROR_MODEL_LOADING = "⚠️ The model is still loading, please try again in a moment"

def get_response(prompt: str) -> str:
    """
    Generate a response using the local Flan-T5 model.
    Uses 8-bit quantization for memory efficiency.
    """
    if not prompt or not prompt.strip():
        logger.warning("Empty prompt received")
        return ERROR_EMPTY_INPUT
    
    try:
        # Format prompt for customer support context
        formatted_prompt = f"Answer politely as a customer support agent: {prompt.strip()}"
        
        # Tokenize input
        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            max_length=MAX_LENGTH,
            truncation=True
        ).to(model.device)
        
        # Generate response
        with torch.inference_mode():
            outputs = model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=MAX_LENGTH,
                temperature=TEMPERATURE,
                do_sample=True,
                top_p=0.95,
                num_return_sequences=1
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        if response:
            logger.info(f"Generated response: {response}")
            return response.strip()
        else:
            logger.error("Empty response generated")
            return ERROR_PROCESSING
            
    except Exception as e:
        logger.exception("Error generating response:")
        return ERROR_PROCESSING
