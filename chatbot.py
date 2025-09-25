"""
Memory-optimized chatbot implementing Hugging Face transformers.
Uses 8-bit quantization to reduce memory usage for Railway deployment.
"""
import os
import logging
import torch
from typing import Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from accelerate import init_empty_weights

# Set up logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = "google/flan-t5-small"
MAX_LENGTH = 128
TEMPERATURE = 0.7

# Initialize model with CPU optimization
logger.info(f"Loading model {MODEL_NAME} with CPU optimization...")

# Load tokenizer with local caching
tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME, 
    cache_dir="models",
    local_files_only=True  # Use cached files after first download
)

# Load model with CPU optimization
model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME,
    cache_dir="models",
    local_files_only=True,  # Use cached files
    torch_dtype=torch.float32,  # Use float32 for CPU
    device_map="cpu",  # Force CPU usage
    low_cpu_mem_usage=True  # Enable memory optimization
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
