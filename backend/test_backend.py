import requests
import time

def test_generate():
    url = "http://127.0.0.1:5050/generate"
    data = {
        "text": "Tesla",
        "description": "Electric cars and sustainable energy",
        "style": "tech",
        "palette": "neon"
    }
    
    print(f"Testing /generate with: {data}")
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            result = response.json()
            print("Successfully generated logo!")
            print(f"Brand: {result['brand']}")
            print(f"Result (first 100 chars): {result['result'][0][:100]}...")
            return True
        else:
            print(f"Failed: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    # Wait a bit for server to start if needed
    test_generate()
