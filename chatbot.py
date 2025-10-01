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
TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", 0.2))
NUM_BEAMS = int(os.getenv("MODEL_NUM_BEAMS", 4))
REPETITION_PENALTY = float(os.getenv("MODEL_REPETITION_PENALTY", 1.2))
NO_REPEAT_NGRAM_SIZE = int(os.getenv("MODEL_NO_REPEAT_NGRAM_SIZE", 3))

# System prompt to guide the assistant's behaviour and keep replies focused/deterministic
SYSTEM_PROMPT = """
You are Catanduanes Connect Assistant, an AI chatbot integrated into the Catanduanes Connect system.

🎯 PURPOSE:
- Help users with business directories, job listings, and location services in Catanduanes.
- Provide clear, short, and accurate responses.
- Always stay on topic and refuse unrelated questions politely.

⚙️ BEHAVIOR RULES:
1. If the question is about jobs → direct to the job portal section.
2. If the question is about businesses → guide them to the directory or GIS map.
3. If the system cannot provide information → reply:
   'I don’t have that information right now. Please check the latest updates on the app.'
4. Never generate random or unrelated answers.
5. Be polite, professional, and user-friendly.

🔧 DEV NOTE:
- Default temperature = 0.2 (for focused responses).
- You can increase temperature up to 0.5 for more variety, or lower it to 0.0 for strict, deterministic answers.
"""


def _route_prompt(text: str) -> str | None:
    """
    Simple deterministic router for common app-specific requests.
    Returns a short direct response string when it matches, otherwise None.
    """
    if not text:
        return None
    t = text.lower()

    # Jobs-related
    if any(k in t for k in ("job", "jobs", "job portal", "job listing", "hiring", "vacancy", "vacancies")):
        return (
            "For job listings, please visit the Job Portal in the app (Jobs section). "
            "You can also search or filter jobs from the Jobs page to find openings."
        )

    # Businesses / directory
    if any(k in t for k in ("business", "businesses", "directory", "company", "companies", "business listing")):
        return (
            "To find businesses, please use the Directory in the app or the Business Search page. "
            "You can also view businesses on the Map for location details."
        )

    # Map / GIS
    if any(k in t for k in ("map", "location", "gis", "coordinates", "where is", "address", "find")):
        return (
            "Use the Map page or the GIS map in the Directory to find locations and coordinates. "
            "Open the Map from the main menu to see business and place pins."
        )

    return None

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
        # First, check deterministic router for app-specific intents (jobs, businesses, map)
        routed = _route_prompt(prompt)
        if routed:
            return routed

        # Build the prompt for the model using the system prompt provided above.
        # This keeps the assistant on-topic and instructs it to refuse unrelated requests.
        formatted_prompt = (
            SYSTEM_PROMPT.strip() + "\n\n"
            + f"User: {prompt.strip()}\nAssistant:"
        )

        import torch
        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            max_length=MAX_LENGTH,
            truncation=True
        ).to(model.device)

        with torch.inference_mode():
            # Determine sampling behavior: when temperature > 0 use sampling for more variety;
            # when temperature == 0 prefer beam search / deterministic generation.
            do_sample = bool(TEMPERATURE and float(TEMPERATURE) > 0.0)
            gen_kwargs = dict(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=MAX_LENGTH,
                num_beams=NUM_BEAMS if not do_sample else 1,
                repetition_penalty=REPETITION_PENALTY,
                no_repeat_ngram_size=NO_REPEAT_NGRAM_SIZE,
                early_stopping=not do_sample,
                do_sample=do_sample,
            )
            if do_sample:
                gen_kwargs.update({
                    "temperature": float(TEMPERATURE),
                    "top_p": 0.95,
                })

            outputs = model.generate(**gen_kwargs)

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
