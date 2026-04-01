import requests
import base64
import json
import time
import os

API_URL = "http://127.0.0.1:8000/solve"

def image_to_base64(filepath):
    try:
        if not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"[-] Error loading image: {e}")
        return None

def test_grid():
    print("\n--- TEST 1: GRID MODE (test.png) ---")
    img_path = os.path.join(os.path.dirname(__file__), "..", "test.png")
    img_b64 = image_to_base64(img_path)
    
    if not img_b64:
        print("[-] Skipping Grid Test. test.png not found.")
        return

    payload = {
        "prompt": "Click on animals taller than the one in the example",
        "type": "grid",
        "grid_images": [img_b64] # Sending 1 large grid image (Server will auto-crop)
    }

    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"[SUCCESS] Result: {data.get('click_indices')}")
            if data.get('click_indices'):
                print("✅ Grid Test Passed!")
        else:
            print(f"[-] API Error: {response.text}")
    except Exception as e:
        print(f"[-] Connection Error: {e}")

def test_collage():
    print("\n--- TEST 2: COLLAGE MODE (test2.png) ---")
    img_path = os.path.join(os.path.dirname(__file__), "..", "test2.png")
    img_b64 = image_to_base64(img_path)
    
    if not img_b64:
        print("[-] Skipping Collage Test. test2.png not found.")
        return

    payload = {
        "prompt": "Click on the vehicle that travels exclusively on tracks",
        "type": "collage",
        "grid_images": [img_b64] # In collage mode, we always send the full image
    }

    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            data = response.json()
            coords = data.get('click_coords')
            print(f"[SUCCESS] Coordinates: {coords}")
            if coords:
                print("✅ Collage Test Passed!")
        else:
            print(f"[-] API Error: {response.text}")
    except Exception as e:
        print(f"[-] Connection Error: {e}")

if __name__ == "__main__":
    print("[*] Starting HCaptcha Multi-Mode Test...")
    test_grid()
    test_collage()
