
import sys
import os
import numpy as np
from navec import Navec

# Add app to path
sys.path.append(os.getcwd())

from app.embeddings import NAVEC_MODEL_NAME, EmbeddingsService

def run_experiment():
    print("Loading model...")
    service = EmbeddingsService()
    service.load_model()
    
    # 1. Check Frequency Assumption
    print("\n--- Experiment 1: Frequency/Age Check ---")
    words = service.words_list
    print(f"Total words: {len(words)}")
    print("First 10 words (most frequent?):", words[:10])
    print("Words around 1000:", words[1000:1010])
    print("Words around 100,000:", words[100000:100010])
    print("Last 10 words (least frequent?):", words[-10:])
    
    # Check specific words indices
    test_words = ["мама", "сингулярность", "экзистенциальный", "дом", "кошка"]
    for w in test_words:
        try:
            idx = words.index(w)
            print(f"Word '{w}' index: {idx}")
        except ValueError:
            print(f"Word '{w}' not found")

    # 2. Check Semantic Compatibility for Phrases
    print("\n--- Experiment 2: Phrase Compatibility (Cosine Similarity) ---")
    
    pairs = [
        ("медведь", "бурый"), # Good
        ("медведь", "утюжный"), # Bad
        ("трава", "зеленая"), # Good
        ("трава", "раскрепощенная"), # Bad
        ("небо", "голубое"), # Good
        ("небо", "кирпичное"), # Bad (or at least weird)
    ]
    
    for noun, adj in pairs:
        vec_noun = service.get_embedding(noun)
        vec_adj = service.get_embedding(adj)
        
        if vec_noun is not None and vec_adj is not None:
            sim = service._cosine_similarity(vec_noun, vec_adj)
            print(f"Similarity '{adj} {noun}': {sim:.4f}")
        else:
            print(f"Words not found: {noun}, {adj}")

if __name__ == "__main__":
    run_experiment()
