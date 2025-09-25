from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import os

def download_and_save_model():
    model_name = "google/flan-t5-small"
    save_dir = "./model"

    # Make sure the folder exists
    os.makedirs(save_dir, exist_ok=True)

    print(f"🔽 Downloading {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    print(f"💾 Saving model and tokenizer to {save_dir}...")
    tokenizer.save_pretrained(save_dir)
    model.save_pretrained(save_dir)

    print("✅ Model saved successfully. Files inside ./model/:")
    for f in os.listdir(save_dir):
        print("   -", f)

if __name__ == "__main__":
    download_and_save_model()
