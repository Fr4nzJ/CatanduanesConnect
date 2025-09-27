"""
Memory-optimized chatbot with lazy loading.
Falls back to Hugging Face Hub if local ./model is missing or corrupted.
"""
import os
import logging
import torch
from typing import Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# Set up logging
logger = logging.getLogger(__name__)

# Config
MAX_LENGTH = 128
TEMPERATURE = 0.7
DEFAULT_MODEL = "google/flan-t5-small"  # Small, safe fallback model

# Globals (lazy loaded)
tokenizer = None
model = None

# Error messages
ERROR_EMPTY_INPUT = "⚠️ Please provide a message"
ERROR_PROCESSING = "⚠️ Error processing your request"
ERROR_MODEL_LOADING = "⚠️ The model is still loading, please try again later"

def load_model():
    """
    Lazily load the model and tokenizer.
    Tries ./model first, otherwise downloads from Hugging Face Hub.
    """
    global tokenizer, model
    if tokenizer is not None and model is not None:
        return tokenizer, model

    try:
        local_model_path = os.path.join(os.path.dirname(__file__), "model")
        if os.path.isdir(local_model_path):
            logger.info("Attempting to load local model from ./model ...")
            try:
                tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=False)
                model = AutoModelForSeq2SeqLM.from_pretrained(
                    local_model_path,
                    torch_dtype=torch.float32,
                    device_map="cpu",
                    low_cpu_mem_usage=True
                )
                logger.info("✓ Local model loaded successfully")
                return tokenizer, model
            except Exception as e:
                logger.error(f"Local model load failed: {e}. Falling back to Hugging Face Hub...")

        # Fallback → download from Hugging Face
        logger.info(f"Loading fallback model: {DEFAULT_MODEL}")
        tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL, use_fast=True)
        model = AutoModelForSeq2SeqLM.from_pretrained(
            DEFAULT_MODEL,
            torch_dtype=torch.float32,
            device_map="cpu"
        )
        logger.info("✓ Fallback model loaded successfully")
    except Exception as e:
        logger.exception("Failed to load any model")
        tokenizer, model = None, None

    return tokenizer, model

def get_response(prompt: str) -> str:
    """
    Generate a response using the chatbot model.
    """
    if not prompt or not prompt.strip():
        logger.warning("Empty prompt received")
        return ERROR_EMPTY_INPUT

    tokenizer, model = load_model()
    if tokenizer is None or model is None:
        return ERROR_MODEL_LOADING

    try:
        formatted_prompt = f"Answer politely as a customer support agent: {prompt.strip()}"

        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            max_length=MAX_LENGTH,
            truncation=True
        ).to(model.device)

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

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response.strip() if response else ERROR_PROCESSING
    except Exception as e:
        logger.exception("Error generating response:")
        return ERROR_PROCESSING
