import socket

def test_raw_request():
    host = "localhost"
    port = 8081
    # Raw bytes with unencoded Cyrillic
    path = "/api/words?word=медведь&phrase_length=2"
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
    
    print(f"Sending raw request to {host}:{port}")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(request.encode('utf-8')) # Encoding as utf-8, so sending raw bytes
        
        response = b""
        while True:
            data = s.recv(4096)
            if not data:
                break
            response += data
        s.close()
        
        print("Response:")
        print(response.decode('utf-8', errors='replace'))
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_raw_request()
