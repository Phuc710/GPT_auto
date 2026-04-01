import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_stripe_api(card):
    url = f"https://stripe.melmelmel.workers.dev/?card={card}"
    print(f"Testing API with card: {card}")
    try:
        resp = requests.get(url, timeout=30, verify=False)
        ms = int(resp.elapsed.total_seconds() * 1000)
        print(f"Status Code: {resp.status_code} ({ms}ms)")
        print(f"Response: {resp.text}")
        data = resp.json()
        print(f"JSON data: {json.dumps(data, indent=2)}")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    # Test with a dummy card
    test_stripe_api("6258142603698669|05|27|927")
