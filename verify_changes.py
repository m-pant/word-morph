
import requests
import json
import time
import subprocess
import sys

import os

BASE_URL = os.getenv("WORD_MORPH_API_URL", "http://localhost:8081") + "/api/words"
HEALTH_URL = os.getenv("WORD_MORPH_API_URL", "http://localhost:8081") + "/health"

def test_phrases():
    print("\n--- Testing Phrase Generation ---")
    params = {
        "word": "медведь",
        "count": 5,
        "phrase_length": 2
    }
    try:
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            print("Results:", data['results'])
            # Check if results are phrases (contain space)
            for res in data['results']:
                if " " not in res:
                    print(f"FAIL: '{res}' is not a phrase")
                else:
                    print(f"PASS: '{res}' is a phrase")
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

def test_age_filter():
    print("\n--- Testing Age Filter ---")
    # 1. Young child (7 years) - should not have "сингулярность"
    params_young = {
        "word": "наука",
        "count": 10,
        "age": 7
    }
    response = requests.get(BASE_URL, params=params_young)
    if response.status_code == 200:
        results = response.json()['results']
        print(f"Age 7 results: {results}")
        # Check for complex words (heuristic)
        complex_words = ["сингулярность", "экзистенциальный", "парадигма"]
        if any(w in results for w in complex_words):
             print("FAIL: Found complex words for age 7")
        else:
             print("PASS: No obvious complex words for age 7")
             
    # 2. Adult - should have more complex words
    params_adult = {
        "word": "наука",
        "count": 10,
        "age": 25
    }
    response = requests.get(BASE_URL, params=params_adult)
    if response.status_code == 200:
        results = response.json()['results']
        print(f"Age 25 results: {results}")

def test_global_skip():
    print("\n--- Testing Global Skip ---")
    params = {
        "word": "медведь",
        "count": 1,
        "phrase_length": 2,
        "skip_letters": 3,
        "global_skip": True,
        "show_skipped": True
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        results = response.json()['results']
        print(f"Global skip results: {results}")
        for res in results:
            underscores = res.count('_')
            print(f"Phrase: '{res}', Underscores: {underscores}")
            if underscores == 3:
                print("PASS: Correct number of skips")
            else:
                print(f"FAIL: Expected 3 skips, got {underscores}")

def run_server_and_test():
    # In Docker mode, we assume server is already running (via depends_on)
    # But we can still check health
    
    # If running locally (not in docker), start server
    server_process = None
    if "WORD_MORPH_API_URL" not in os.environ:
        print("Starting server locally...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8081"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(5)

    try:
        # Wait for server to start
        print(f"Checking server at {HEALTH_URL}...")
        for i in range(60):
            try:
                response = requests.get(HEALTH_URL)
                if response.status_code == 200:
                    print("Server is ready!")
                    break
            except requests.exceptions.ConnectionError:
                time.sleep(1)
                print(f"Waiting... {i+1}/60")
        else:
            print("Server failed to respond in 60 seconds")
            if server_process:
                server_process.terminate()
            return

        test_phrases()
        test_age_filter()
        test_global_skip()
    finally:
        if server_process:
            print("\nStopping local server...")
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    run_server_and_test()
