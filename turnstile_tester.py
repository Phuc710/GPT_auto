import time
import random
import os
import re
import subprocess
import sys
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Tắt buffer terminal để log hiện ra ngay lập tức
sys.stdout.reconfigure(line_buffering=True)

def solve_turnstile(driver):
    try:
        current_time = time.strftime('%H:%M:%S')
        print(f"[{current_time}] 🔎 Bắt đầu quét trang tìm Turnstile...")
        
        # 1. Liệt kê tất cả iframe hiện có trên trang để debug
        try:
            all_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if not all_iframes:
                print(f"[{current_time}] ⚪ Không tìm thấy bất kỳ iframe nào trên trang.")
                return False
            else:
                print(f"[{current_time}] 📄 Tìm thấy {len(all_iframes)} iframe(s). Đang kiểm tra từng cái...")
        except Exception as e:
            print(f"[{current_time}] ❌ Lỗi khi lấy danh sách iframe: {e}")
            return False
            
        target_frame = None
        for i, frame in enumerate(all_iframes):
            try:
                src = frame.get_attribute("src") or ""
                id_attr = frame.get_attribute("id") or "no-id"
                visible = frame.is_displayed()
                width = frame.size['width']
                height = frame.size['height']
                
                if "challenges.cloudflare.com" in src:
                    print(f"[{current_time}] ✨ FRAME #{i} KHỚP: ID={id_attr}, Visible={visible}, Size={width}x{height}")
                    if width > 0 and height > 0:
                        target_frame = frame
                        break
                    else:
                        print(f"[{current_time}] ⚠️ Frame khớp nhưng kích thước bằng 0, có thể là frame chạy ngầm.")
                else:
                    # Log nhẹ các frame khác để biết Bot có đang hoạt động không
                    if i < 3: # Chỉ log 3 cái đầu cho đỡ rác
                        print(f"[{current_time}]    [-] Frame #{i}: src={src[:50]}...")
            except Exception as e:
                continue
        
        if not target_frame:
            print(f"[{current_time}] 💤 Không tìm thấy Iframe Turnstile (Cloudflare) phù hợp.")
            return False
            
        # 2. Kiểm tra trạng thái đã giải chưa
        print(f"[{current_time}] 🛰️ Đang kiểm tra trường 'cf-turnstile-response'...")
        try:
            token = driver.execute_script("return document.querySelector('[name=\"cf-turnstile-response\"]')?.value")
            if token and len(token) > 10:
                print(f"[{current_time}] ✅ Đã có Token ({token[:10]}...). Bỏ qua vì đã giải xong.")
                return True
            else:
                print(f"[{current_time}] 🔓 Chưa có Token. Bắt đầu công phá...")
        except Exception as e:
            print(f"[{current_time}] ❌ Lỗi khi check token: {e}")

        # 3. Tiến hành giải
        print(f"[{current_time}] ⚡ Đang chuyển context vào Iframe: {target_frame.get_attribute('id')}...")
        driver.switch_to.frame(target_frame)
        
        print(f"[{current_time}] 🖱️ Đang giả lập Click tại tọa độ (30, 32) bằng JavaScript...")
        driver.execute_script("""
            let el = document.elementFromPoint(30, 32);
            if (!el) {
                console.log('Không tìm thấy element tại 30,32, thử tìm label...');
                el = document.querySelector('label.cb-lb') || document.querySelector('input[type="checkbox"]');
            }
            if (el) {
                ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click'].forEach(type => {
                    el.dispatchEvent(new MouseEvent(type, {
                        view: window, bubbles: true, cancelable: true, buttons: 1, clientX: 30, clientY: 32
                    }));
                });
                return true;
            }
            return false;
        """)
        
        # Bồi thêm ActionChains
        print(f"[{current_time}] 🥊 Đang bồi thêm cú đấm vật lý (ActionChains)...")
        try:
            body = driver.find_element(By.TAG_NAME, 'body')
            ActionChains(driver).move_to_element(body).move_by_offset(-120, 0).click().perform()
        except Exception as e:
            print(f"[{current_time}] ⚠️ Lỗi khi click vật lý: {e}")

        print(f"[{current_time}] 🏁 Đã xử lý xong, quay lại main page...")
        driver.switch_to.default_content()
        
        # Đợi 3 giây xem kết quả
        print(f"[{current_time}] ⏳ Chờ 3 giây để Cloudflare verify...")
        time.sleep(3)
        
        final_token = driver.execute_script("return document.querySelector('[name=\"cf-turnstile-response\"]')?.value")
        if final_token and len(final_token) > 10:
            print(f"[{current_time}] 🏆 CHÚC MỪNG! Giải thành công. Token: {final_token[:15]}...")
            return True
        else:
            print(f"[{current_time}] ❌ Vẫn chưa thấy Token. Có thể cần click lại hoặc Captcha này khó.")
            
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 🧨 Lỗi nghiêm trọng: {e}")
    return False

def get_chrome_version():
    try:
        browser_path = uc.find_chrome_executable()
        if not browser_path: return None
        ps_command = f"(Get-Item '{browser_path}').VersionInfo.ProductVersion"
        result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True, timeout=5)
        match = re.search(r"(\d+)\.", result.stdout)
        if match:
            return int(match.group(1))
    except:
        pass
    return None

if __name__ == "__main__":
    version = get_chrome_version()
    print(f"Detected Chrome version: {version}")
    
    options = uc.ChromeOptions()
    # options.add_argument("--auto-open-devtools-for-tabs")
    
    try:
        print("🔧 Khởi tạo trình duyệt...")
        driver = uc.Chrome(options=options, version_main=version)
        print("\n🚀 PYTHON BOT DEBUG MODE ĐÃ CHẠY!")
        print("💡 Bot sẽ log TẤT CẢ các bước. Mày hãy quan sát Terminal.\n")
        
        # Thử vào trang test
        print("🔗 Điều hướng tới: https://kaishop.id.vn/login")
        driver.get("https://kaishop.id.vn/login")
        
        while True:
            try:
                solve_turnstile(driver)
                time.sleep(3) # Quét mỗi 3s cho đỡ spam log
            except Exception as e:
                print(f"⚠️ Lỗi vòng lặp: {e}")
                time.sleep(1)
                continue
                
    except KeyboardInterrupt:
        print("\n👋 Đã tắt BOT.")
    except Exception as e:
        print(f"\n❌ Lỗi khởi động: {e}")
    finally:
        print("\n[HẾT] Trình duyệt vẫn đang mở.")
