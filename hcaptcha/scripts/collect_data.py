import os
import time
import requests
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

# --- Configuration ---
SAVE_DIR = "c:/Users/Phucc/Desktop/GPT/hcapcha/dataset/raw"
DEMO_URL = "https://accounts.hcaptcha.com/demo" # Or any site with HCaptcha

class HCaptchaScraper:
    def __init__(self):
        options = uc.ChromeOptions()
        # options.add_argument("--headless") # Headless mode for background scraping
        # Specifying version_main to match user's browser version (146)
        self.driver = uc.Chrome(options=options, version_main=146)
        self.wait = WebDriverWait(self.driver, 10)

    def scrape(self, iterations=50):
        if not os.path.exists(SAVE_DIR):
            os.makedirs(SAVE_DIR)

        for i in range(iterations):
            print(f"[*] Iteration {i+1}/{iterations}...")
            try:
                self.driver.get(DEMO_URL)
                
                # 1. Switch to checkbox iframe
                self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, "iframe[title*='checkbox']")))
                
                # 2. Click checkbox
                checkbox = self.wait.until(EC.element_to_be_clickable((By.ID, "checkbox")))
                checkbox.click()
                print("[+] Clicked checkbox")
                
                # 3. Handle Challenge Iframe
                self.driver.switch_to.default_content()
                time.sleep(2) # Wait for challenge to pop
                
                challenge_frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe[title*='content']")
                if not challenge_frames:
                    print("[!] No image challenge appeared (Passive skip).")
                    continue
                
                self.driver.switch_to.frame(challenge_frames[0])
                
                # 4. Extract Prompt & Type
                prompt_el = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".prompt-text")))
                prompt_text = prompt_el.text.strip().replace(" ", "_").lower()
                print(f"[+] Prompt: {prompt_text}")
                
                # Create directory for this prompt
                target_dir = os.path.join(SAVE_DIR, prompt_text)
                if not os.path.exists(target_dir):
                    os.makedirs(target_dir)

                # 5. Check if it's a Grid (3x3/4x4) or Relational
                # Look for reference image
                ref_images = self.driver.find_elements(By.CSS_SELECTOR, ".challenge-image img") # Reference if exists
                tiles = self.driver.find_elements(By.CSS_SELECTOR, ".task-image .image") # Grid tiles

                if tiles:
                    print(f"[+] Grid detected with {len(tiles)} tiles.")
                    for idx, tile in enumerate(tiles):
                        style = tile.get_attribute("style")
                        # Extract URL from: background-image: url("https://...");
                        if 'url("' in style:
                            img_url = style.split('url("')[1].split('")')[0]
                            self.download_image(img_url, target_dir)
                
                # Relational / Contextual collage (as seen in screenshot)
                collage = self.driver.find_elements(By.CSS_SELECTOR, ".challenge-container .image-wrapper")
                if collage:
                    print("[+] Relational/Collage detected.")
                    # In real-time, you'd capture the main canvas or individual layered images
                    # Here we save whatever is available in the DOM
                    # ... (Logic to capture layered images) ...
                
                # 6. Close/Refresh for next iteration
                print("[*] Transitioning to next challenge...")
                time.sleep(1)
                
            except Exception as e:
                print(f"[-] Error: {e}")
                time.sleep(2)

    def download_image(self, url, folder):
        try:
            name = f"{uuid.uuid4().hex}.jpg"
            path = os.path.join(folder, name)
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(response.content)
        except:
            pass

if __name__ == "__main__":
    scraper = HCaptchaScraper()
    scraper.scrape(iterations=100)
    scraper.driver.quit()
