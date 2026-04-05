import requests
from bs4 import BeautifulSoup

url = "https://proxycompass.com/free-proxy/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')
        if table:
            # Print first 2 rows to understand structure
            rows = table.find_all('tr')
            for i, row in enumerate(rows[:3]):
                print(f"Row {i}: {row.get_text(separator=' | ').strip()}")
        else:
            print("Table not found")
except Exception as e:
    print(f"Error: {e}")
