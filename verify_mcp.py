import requests
import json
import time

def test_mcp_search():
    url = "http://localhost:8082/search"
    payload = {
        "word": "медведь",
        "phrase_length": 3,
        "age": 7,
        "global_skip": True,
        "skip_letters": 1,
        "show_skipped": True
    }
    
    print(f"Testing MCP Search: {url}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for MCP server...")
    time.sleep(5)
    test_mcp_search()
