"""
Memory-optimized chatbot for Flask + Hugging Face transformers.
- Lazy loads model/tokenizer on first request (not at import time).
- Always tries local ./model first (with use_fast=False).
- Falls back to Hugging Face "google/flan-t5-small" (with use_fast=True) if local model is missing/incomplete.
- Returns safe error messages if model loading fails.
- Optimized for Railway free tier (≤ 3 GB RAM, CPU only).
"""

import os
import logging

# Error messages
ERROR_EMPTY_INPUT = "Please provide a message"
ERROR_PROCESSING = "Error processing your request"
ERROR_MODEL_LOADING = "The model is not available right now, please try again later"

# Model config
DEFAULT_MODEL = "google/flan-t5-small"
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
MAX_LENGTH = int(os.getenv("MODEL_MAX_LENGTH", 128))
TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", 0.0))
NUM_BEAMS = int(os.getenv("MODEL_NUM_BEAMS", 4))
REPETITION_PENALTY = float(os.getenv("MODEL_REPETITION_PENALTY", 1.2))
NO_REPEAT_NGRAM_SIZE = int(os.getenv("MODEL_NO_REPEAT_NGRAM_SIZE", 3))

# Globals for lazy loading
tokenizer = None
model = None
load_failed = False

def _is_local_model_available():
    # Must be a directory and contain spiece.model (for T5 tokenizer)
    if not isinstance(LOCAL_MODEL_DIR, str):
        return False
    if not os.path.isdir(LOCAL_MODEL_DIR):
        return False
    if not os.path.isfile(os.path.join(LOCAL_MODEL_DIR, "spiece.model")):
        return False
    return True

def _lazy_load():
    global tokenizer, model, load_failed
    if tokenizer is not None and model is not None:
        return True
    if load_failed:
        return False

    try:
        # Import transformers/torch only when needed
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        if _is_local_model_available():
            logging.info("Loading local model from ./model (use_fast=False)...")
            tokenizer = AutoTokenizer.from_pretrained(LOCAL_MODEL_DIR, use_fast=False)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                LOCAL_MODEL_DIR,
                torch_dtype=torch.float32,
                device_map="cpu",
                low_cpu_mem_usage=True
            )
            logging.info("✓ Local model loaded successfully")
        else:
            logging.info("Local model not found or incomplete, falling back to Hugging Face Hub...")
            tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL, use_fast=True)
            model = AutoModelForSeq2SeqLM.from_pretrained(
                DEFAULT_MODEL,
                torch_dtype=torch.float32,
                device_map="cpu"
            )
            logging.info("✓ Fallback model loaded successfully")
        return True
    except Exception as e:
        logging.exception(f"Failed to load model/tokenizer: {e}")
        tokenizer, model = None, None
        load_failed = True
        return False

def get_response(prompt: str) -> str:
    """
    Generate a response using the chatbot model.
    Returns safe error messages if model/tokenizer are unavailable.
    """
    if not prompt or not prompt.strip():
        logging.warning("Empty prompt received")
        return ERROR_EMPTY_INPUT

    if not _lazy_load():
        return ERROR_MODEL_LOADING

    try:
        # System prompt: discourage parroting, keep answers concise
        formatted_prompt = (
            "You are a helpful, concise customer support assistant. "
            "Answer politely and directly, focusing only on information relevant to the user's question. "
            "Do NOT repeat the user's exact phrasing back verbatim; instead, summarize or respond directly. "
            "If the user provides praise or insults, acknowledge briefly but do not echo the phrase.\n\n"
            f"User: {prompt.strip()}\nAssistant:"
        )

        import torch
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
                num_beams=NUM_BEAMS,
                repetition_penalty=REPETITION_PENALTY,
                no_repeat_ngram_size=NO_REPEAT_NGRAM_SIZE,
                early_stopping=True,
                do_sample=False
            )

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response.strip() if response else ERROR_PROCESSING
    except Exception as e:
        logging.exception("Error generating response:")
        return ERROR_PROCESSING

# Optional: Logging filter to skip empty request bodies
class SkipEmptyBodyFilter(logging.Filter):
    def filter(self, record):
        # Only filter Flask request body logs
        msg = getattr(record, 'msg', '')
        if isinstance(msg, str) and 'Body:' in msg and 'Body: b\'\'' in msg:
            return False
        return True

# To use the filter, add to your Flask app logger setup:
# app.logger.addFilter(SkipEmptyBodyFilter())
