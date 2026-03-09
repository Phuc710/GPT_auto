import time
import random
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ============ CONFIG ============
PROFILE_DIR = Path(__file__).resolve().parent / ".google_family_profile"
FAMILY_URL = "https://myaccount.google.com/family/details"

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Tắt automation detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    try:
        # Bỏ version_main để driver tự động tải bản khớp với trình duyệt
        driver = uc.Chrome(options=options, headless=False)
        return driver
    except Exception as e:
        print(f"❌ Không khởi động được trình duyệt: {e}")
        return None

def auto_add_family(target_email):
    driver = create_driver()
    if not driver:
        return

    try:
        print(f"🌐 Đang truy cập: {FAMILY_URL}")
        driver.get(FAMILY_URL)
        
        # Đợi trang load
        time.sleep(3)
        
        # KIỂM TRA ĐĂNG NHẬP
        if "signin" in driver.current_url:
            print("⚠️ Mày chưa đăng nhập Google! Hãy đăng nhập tay trong trình duyệt đang mở...")
            # Đợi đến khi URL không còn là signin
            while "signin" in driver.current_url:
                time.sleep(2)
            print("✅ Đã phát hiện đăng nhập thành công.")
            driver.get(FAMILY_URL) # Quay lại trang family
            time.sleep(3)

        # 1. Tìm nút "Gửi lời mời" (Invite)
        # Thường có text: "Gửi lời mời" hoặc dấu "+"
        print("🔍 Đang tìm nút mời thành viên...")
        invite_selectors = [
            "//span[contains(text(), 'Gửi lời mời')]",
            "//div[@role='button']//span[contains(text(), 'Invite')]",
            "//button[contains(., 'Invite')]",
            "//i[contains(@class, 'add')]" # Icon cộng
        ]
        
        found_btn = None
        for selector in invite_selectors:
            try:
                found_btn = driver.find_element(By.XPATH, selector)
                if found_btn:
                    found_btn.click()
                    print(f"✅ Đã click nút mời (bằng: {selector})")
                    break
            except:
                continue
        
        if not found_btn:
            # Fallback: Click nút có text "Gửi lời mời" bằng JS
            driver.execute_script("""
                var spans = document.querySelectorAll('span, div, button');
                for(var i=0; i<spans.length; i++){
                    if(spans[i].textContent.includes('Gửi lời mời') || spans[i].textContent.includes('Invite')){
                        spans[i].click();
                        break;
                    }
                }
            """)
            print("⚡ Đã thử click bằng JavaScript fallback.")

        time.sleep(2)

        # 2. Nhập Email
        print(f"⌨️ Đang nhập Gmail: {target_email}")
        try:
            wait = WebDriverWait(driver, 10)
            email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @type='text']")))
            email_input.clear()
            for char in target_email:
                email_input.send_keys(char)
                time.sleep(random.uniform(0.1, 0.2))
            
            time.sleep(1)
            
            # Click nút "Gửi" hoặc "Tiếp theo"
            driver.execute_script("""
                var btns = document.querySelectorAll('span, div, button');
                for(var i=0; i<btns.length; i++){
                    if(btns[i].textContent.trim() === 'Gửi' || btns[i].textContent.trim() === 'Send' || btns[i].textContent.trim() === 'Next'){
                        btns[i].click();
                        break;
                    }
                }
            """)
            print("🚀 Đã gửi lời mời!")
            
        except TimeoutException:
            print("❌ Không tìm thấy ô nhập Email.")

        print("\n🎉 Xong rồi! Mày có thể tắt trình duyệt.")
        time.sleep(5)

    except Exception as e:
        print(f"💥 Lỗi hệ thống: {e}")
    finally:
        # driver.quit() # Tắt cái này nếu muốn mày tự check kết quả
        pass

if __name__ == "__main__":
    email = input("Nhập Gmail cần add vào Family: ")
    auto_add_family(email)
