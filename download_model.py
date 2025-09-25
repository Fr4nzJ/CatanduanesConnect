"""
Helper script to download and save the flan-t5-small model locally.
Run this script on a machine with internet access before deployment.
"""
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os

def download_model():
    model_name = "google/flan-t5-small"
    save_dir = os.path.join(os.path.dirname(__file__), "model")
    
    print(f"Downloading model {model_name}...")
    
    # Create directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Download and save tokenizer
    print("Downloading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    tokenizer.save_pretrained(save_dir)
    print("✓ Tokenizer saved")
    
    # Download and save model
    print("Downloading model...")
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        torch_dtype="auto",  # Use the most efficient dtype for CPU
        device_map="cpu",    # Force CPU usage
        low_cpu_mem_usage=True
    )
    model.save_pretrained(save_dir)
    print("✓ Model saved")
    
    print(f"\nModel and tokenizer saved to: {save_dir}")
    print("You can now commit this folder to your repository")

if __name__ == "__main__":
    download_model()