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
import math

# Tắt buffer terminal để log hiện ra ngay lập tức
sys.stdout.reconfigure(line_buffering=True)

# --- HELPER FUNCTIONS FOR HUMAN-LIKE MOVEMENT ---
def get_bezier_points(p0, p1, p2, p3, n=25):
    """Tạo đường cong Bezier bậc 3 để mô phỏng di chuyển chuột."""
    points = []
    for i in range(n + 1):
        t = i / n
        x = (1-t)**3 * p0[0] + 3*(1-t)**2 * t * p1[0] + 3*(1-t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2 * t * p1[1] + 3*(1-t) * t**2 * p2[1] + t**3 * p3[1]
        # Thêm một chút nhiễu (jitter)
        x += random.uniform(-1, 1)
        y += random.uniform(-1, 1)
        points.append((int(x), int(y)))
    return points

def cdp_move_mouse(driver, x, y):
    """Di chuyển chuột qua CDP (bỏ qua mô phỏng JS)."""
    driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
        "type": "mouseMoved",
        "x": x,
        "y": y,
        "button": "none",
        "pointerType": "mouse"
    })

def cdp_click_mouse(driver, x, y):
    """Click chuột vật lý qua CDP tại tọa độ (x, y)."""
    # Mouse Down
    driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
        "type": "mousePressed",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1
    })
    # Giữ nút chuột một lát như người thật
    time.sleep(random.uniform(0.05, 0.12))
    # Mouse Up
    driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
        "type": "mouseReleased",
        "x": x,
        "y": y,
        "button": "left",
        "clickCount": 1
    })

def move_mouse_humanly(driver, start_pos, end_pos):
    """Thực hiện di chuyển chuột từ start tới end theo đường cong Bezier."""
    # Tạo 2 điểm điều khiển (control points) ngẫu nhiên để tạo độ cong
    dist = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
    offset = dist * 0.2
    
    cp1 = (
        start_pos[0] + (end_pos[0] - start_pos[0]) * 0.3 + random.uniform(-offset, offset),
        start_pos[1] + (end_pos[1] - start_pos[1]) * 0.3 + random.uniform(-offset, offset)
    )
    cp2 = (
        start_pos[0] + (end_pos[0] - start_pos[0]) * 0.7 + random.uniform(-offset, offset),
        start_pos[1] + (end_pos[1] - start_pos[1]) * 0.7 + random.uniform(-offset, offset)
    )
    
    path = get_bezier_points(start_pos, cp1, cp2, end_pos, n=int(dist/10) if dist > 50 else 15)
    
    for px, py in path:
        cdp_move_mouse(driver, px, py)
        time.sleep(random.uniform(0.005, 0.015))

def apply_stealth_mode(driver):
    """Tiêm script để fake fingerprinting và ẩn bot."""
    stealth_js = """
    (() => {
        // 1. Ẩn tag WebDriver
        Object.defineProperty(navigator, 'webdriver', { get: () => false });

        // 2. Fake Canvas Fingerprinting (Thêm nhiễu nhẹ)
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
            const imageData = originalGetImageData.apply(this, arguments);
            const res = imageData.data;
            for (let i = 0; i < res.length; i += 4) {
                res[i] = res[i] + (Math.random() > 0.5 ? 1 : -1);
            }
            return imageData;
        };

        // 3. Fake WebGL Fingerprinting
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Fake Vendor & Renderer
            if (parameter === 37445) return 'Intel Inc.';
            if (parameter === 37446) return 'Intel(R) Iris(TM) Plus Graphics 640';
            return getParameter.apply(this, arguments);
        };

        // 4. Overwrite Languages & Plugins
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'vi'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    })();
    """
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": stealth_js})
    print("[+] Đã kích hoạt chế độ Stealth (Anti-Fingerprinting).")

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
        # Lấy tọa độ tuyệt đối của frame TRƯỚC KHI chuyển context
        frame_location = target_frame.location
        # Tọa độ target trong frame thường là khoảng (30, 32) cho cái checkbox
        abs_x = frame_location['x'] + 30 + random.uniform(-2, 2)
        abs_y = frame_location['y'] + 32 + random.uniform(-2, 2)

        print(f"[{current_time}] ⚡ Đang chuyển context vào Iframe để kiểm tra...")
        driver.switch_to.frame(target_frame)
        
        # Kiểm tra xem có element thực sự ở đó không (nhưng không click bằng JS)
        exists = driver.execute_script("return !!document.elementFromPoint(30, 32);")
        if not exists:
            print(f"[{current_time}] ⚠️ Cảnh báo: Không thấy element tại (30, 32) trong frame.")
        
        driver.switch_to.default_content() # Quay lại main page để dùng tọa độ tuyệt đối

        print(f"[{current_time}] 🖱️ Di chuyển chuột tới điểm checkbox: ({int(abs_x)}, {int(abs_y)})")
        # Giả lập di chuyển từ một vị trí ngẫu nhiên (ví dụ góc màn hình)
        start_x, start_y = random.randint(0, 100), random.randint(0, 100)
        move_mouse_humanly(driver, (start_x, start_y), (abs_x, abs_y))
        
        print(f"[{current_time}] 🥊 Thực hiện cú click vật lý (CDP)...")
        cdp_click_mouse(driver, abs_x, abs_y)

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
        
        # Áp dụng Stealth Mode ngay sau khi khởi tạo
        apply_stealth_mode(driver)
        
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
