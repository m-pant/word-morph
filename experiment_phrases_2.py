
import sys
import os
from navec import Navec
import subprocess

# Add app to path
sys.path.append(os.getcwd())

from app.embeddings import EmbeddingsService

def install_wordfreq():
    try:
        import wordfreq
        print("wordfreq already installed")
    except ImportError:
        print("Installing wordfreq...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wordfreq"])

def run_experiment():
    # Install wordfreq
    install_wordfreq()
    from wordfreq import zipf_frequency

    print("Loading model...")
    service = EmbeddingsService()
    service.load_model()
    
    # 1. Check Neighbors for Collocations
    print("\n--- Experiment 1: Neighbors for Collocations ---")
    test_words = ["небо", "трава", "медведь", "чай"]
    
    for word in test_words:
        print(f"\nNeighbors for '{word}':")
        try:
            # Get top 20 similar words
            similar = service.find_similar_words(word, count=20)
            for w, score in similar:
                print(f"  - {w} ({score:.4f})")
        except Exception as e:
            print(f"Error: {e}")

    # 2. Check Frequency for Age
    print("\n--- Experiment 2: Word Frequency (Age) ---")
    words_to_check = [
        "мама", "дом", "кот", # Simple
        "сингулярность", "экзистенциальный", "прерогатива", # Complex
        "компьютер", "интернет" # Medium
    ]
    
    for w in words_to_check:
        freq = zipf_frequency(w, 'ru')
        print(f"Word '{w}': Zipf freq = {freq}")
        # Zipf scale: 0-8. 
        # > 5: very common
        # 4-5: common
        # < 3: rare

if __name__ == "__main__":
    run_experiment()
