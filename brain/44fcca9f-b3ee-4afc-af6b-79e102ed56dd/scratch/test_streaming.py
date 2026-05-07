import requests
import json

def test_endpoint(path, payload):
    url = f"http://localhost:8000/api{path}"
    print(f"Testing {url}...")
    try:
        response = requests.post(url, json=payload, stream=True)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            print(response.text)
            return

        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data:"):
                    try:
                        data = json.loads(decoded_line[5:])
                        if "token" in data:
                            print(data["token"], end="", flush=True)
                        if "error" in data:
                            print(f"\n[ERROR] {data['error']}")
                    except:
                        pass
        print("\nTest complete.")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    # Test Trivia
    test_endpoint("/ai/trivia", {"messages": [{"role": "user", "content": "Let's play!"}]})
    
    # Test Study
    test_endpoint("/ai/study", {"messages": [{"role": "user", "content": "I'm a beginner, send me a scenario."}]})
