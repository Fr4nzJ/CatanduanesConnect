"""
Memory-optimized chatbot with lazy loading.
Falls back to Hugging Face Hub if local ./model is missing or corrupted.
"""
import os
import logging
try:
    import torch
    TORCH_AVAILABLE = True
except Exception:
    torch = None
    TORCH_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "torch is not installed in this environment. Model loading will be skipped until dependencies are installed."
    )
from typing import Optional
try:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except Exception:
    AutoModelForSeq2SeqLM = None
    AutoTokenizer = None
    TRANSFORMERS_AVAILABLE = False
    logging.getLogger(__name__).warning("transformers library not available. Model/tokenizer loading will be skipped.")

# Set up logging
logger = logging.getLogger(__name__)

# Config
MAX_LENGTH = int(os.getenv('MODEL_MAX_LENGTH', 128))
# Generation defaults: deterministic (beam search) for stable replies in production
TEMPERATURE = float(os.getenv('MODEL_TEMPERATURE', 0.0))
DO_SAMPLE = os.getenv('MODEL_DO_SAMPLE', 'false').lower() in ('1', 'true', 'yes')
NUM_BEAMS = int(os.getenv('MODEL_NUM_BEAMS', 4))
TOP_P = float(os.getenv('MODEL_TOP_P', 0.95))
DEFAULT_MODEL = "google/flan-t5-small"  # Small, safe fallback model

# Globals (lazy loaded)
tokenizer = None
model = None

# Error messages (ASCII-only to avoid console encoding issues)
ERROR_EMPTY_INPUT = "Please provide a message"
ERROR_PROCESSING = "Error processing your request"
ERROR_MODEL_LOADING = "The model is not available right now, please try again later"

def load_model():
    """
    Lazily load the model and tokenizer.
    Tries ./model first, otherwise downloads from Hugging Face Hub.
    """
    global tokenizer, model
    if tokenizer is not None and model is not None:
        return tokenizer, model

    if not TRANSFORMERS_AVAILABLE:
        logger.warning("transformers not installed; skipping model/tokenizer load")
        return None, None

    try:
        local_model_path = os.path.join(os.path.dirname(__file__), "model")
        if os.path.isdir(local_model_path):
            logger.info("Attempting to load local model from ./model ...")
            # Try fast tokenizer first (faster) and fall back to slow tokenizer on error
            try:
                try:
                    tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=True)
                    logger.info("Loaded fast tokenizer from local model")
                except Exception:
                    logger.warning("Fast tokenizer failed for local model; retrying with slow tokenizer")
                    tokenizer = AutoTokenizer.from_pretrained(local_model_path, use_fast=False)

                if TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE:
                    model = AutoModelForSeq2SeqLM.from_pretrained(
                        local_model_path,
                        torch_dtype=torch.float32,
                        device_map="cpu",
                        low_cpu_mem_usage=True
                    )
                else:
                    model = None

                logger.info("✓ Local model (or tokenizer) loaded successfully")
                return tokenizer, model
            except Exception as e:
                logger.exception(f"Local model load failed: {e}. Falling back to Hugging Face Hub...")

        # Fallback → download from Hugging Face
        logger.info(f"Loading fallback model: {DEFAULT_MODEL}")
        # Try fast tokenizer from HF, but fall back to slow tokenizer if needed
        try:
            tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL, use_fast=True)
            logger.info("Loaded fast tokenizer from Hugging Face Hub")
        except Exception:
            logger.warning("Fast tokenizer from HF failed; retrying with slow tokenizer")
            tokenizer = AutoTokenizer.from_pretrained(DEFAULT_MODEL, use_fast=False)

        if TORCH_AVAILABLE and TRANSFORMERS_AVAILABLE:
            model = AutoModelForSeq2SeqLM.from_pretrained(
                DEFAULT_MODEL,
                torch_dtype=torch.float32,
                device_map="cpu"
            )
            logger.info("✓ Fallback model loaded successfully")
        else:
            model = None
            logger.warning("Torch or transformers unavailable: skipped fallback model download; tokenizer loaded only.")
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
        # Clear system-style instruction to keep responses on-topic and concise
        # Include an explicit instruction to avoid parroting the user's exact words
        formatted_prompt = (
            "You are a helpful, concise customer support assistant."
            " Answer politely and directly, focusing only on information relevant to the user's question."
            " Do NOT repeat the user's exact phrasing back verbatim; instead, summarize or respond directly."
            " If the user provides praise or insults, acknowledge briefly but do not echo the phrase.\n\n"
            f"User: {prompt.strip()}\nAssistant:"
        )

        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            max_length=MAX_LENGTH,
            truncation=True
        ).to(model.device)

        with torch.inference_mode():
            gen_kwargs = {
                'input_ids': inputs['input_ids'],
                'attention_mask': inputs['attention_mask'],
                'max_length': MAX_LENGTH,
                'num_return_sequences': 1
            }
            # Add anti-repetition parameters to reduce parroting and looping
            gen_kwargs.update({'repetition_penalty': 1.2, 'no_repeat_ngram_size': 3})
            if DO_SAMPLE:
                gen_kwargs.update({'do_sample': True, 'temperature': TEMPERATURE, 'top_p': TOP_P})
            else:
                # Deterministic decoding via beam search
                gen_kwargs.update({'do_sample': False, 'num_beams': NUM_BEAMS, 'early_stopping': True})

            outputs = model.generate(**gen_kwargs)

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response.strip() if response else ERROR_PROCESSING
    except Exception as e:
        logger.exception("Error generating response:")
        return ERROR_PROCESSING
