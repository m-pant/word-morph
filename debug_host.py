import requests
import urllib.parse

def test_request():
    word = "медведь"
    encoded_word = urllib.parse.quote(word)
    url = f"http://localhost:8081/api/words?word={encoded_word}&phrase_length=2"
    print(f"Testing URL: {url}")
    
    try:
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
        print(f"Headers: {response.headers}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_request()
