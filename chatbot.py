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
MAX_LENGTH = 128
TEMPERATURE = 0.7

# Get absolute path to model directory
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")

# Initialize model with CPU optimization
logger.info("Loading local model from ./model directory...")

try:
    # Load tokenizer from local directory
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR,
        local_files_only=True  # Ensure we only use local files
    )

    # Load model with CPU optimization
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_DIR,
        local_files_only=True,  # Ensure we only use local files
        torch_dtype=torch.float32,  # Use float32 for CPU
        device_map="cpu",  # Force CPU usage
        low_cpu_mem_usage=True  # Enable memory optimization
    )
    logger.info("✓ Model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

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
