# grok_selenium.py - Selenium automation for Grok (x.ai) registration

import json
import time
import sys
import random
import os
import re
import string
import shutil
import subprocess
import tempfile
import threading
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from config import WAIT_TIME, DEFAULT_PASSWORD, USE_ANTI_DETECT, RANDOM_DELAYS, MIN_DELAY_MS, MAX_DELAY_MS
from anti_detect import get_random_user_agent, random_delay, random_scroll, random_typing_delay
from step_tracker import Logger  # Shared logger with colored output


# ============ EXCEPTION ============
class SeleniumException(Exception):
    """Custom exception for Selenium operations"""
    pass

# ============ PAGE DETECTOR ============
class PageDetector:
    @staticmethod
    def wait_for_url_change(driver, old_url: str, timeout: int = 15) -> bool:
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(0.5)
            try:
                new_url = driver.current_url
                if new_url and new_url != old_url:
                    return True
            except Exception:
                pass
        return False
    
    @staticmethod
    def wait_for_element_present(driver, locator: tuple, timeout: int = 15) -> bool:
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    @staticmethod
    def wait_for_element_clickable(driver, locator: tuple, timeout: int = 15) -> bool:
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.element_to_be_clickable(locator))
            return True
        except TimeoutException:
            return False

# ============ TIMING MANAGER ============
class TimingManager:
    BASE_DELAYS = {
        "page_load": 3,
        "element_appear": 2,
        "after_click": 2,
        "form_submit": 3,
        "transition": 2,
    }
    
    @staticmethod
    def adaptive_delay(driver, base_delay: float = None) -> float:
        if base_delay is None:
            base_delay = TimingManager.BASE_DELAYS["page_load"]
        try:
            ready_state = driver.execute_script("return document.readyState;")
            if ready_state == "complete":
                return base_delay
            else:
                return base_delay + 2
        except Exception:
            return base_delay
    
    @staticmethod
    def wait_for_stable_state(driver, timeout: int = 15) -> bool:
        start = time.time()
        last_url = ""
        stable_count = 0
        while time.time() - start < timeout:
            try:
                current_url = driver.current_url
                network_idle = driver.execute_script("""
                    return window.performance &&
                           window.performance.timing.loadEventEnd > 0 &&
                           (Date.now() - window.performance.timing.loadEventEnd) > 500;
                """)
                if current_url == last_url and network_idle:
                    stable_count += 1
                    if stable_count >= 2:
                        return True
                else:
                    stable_count = 0
                    last_url = current_url
                time.sleep(0.5)
            except Exception:
                break
        return False
    
    @staticmethod
    def get_action_delay(action_type: str) -> float:
        base = TimingManager.BASE_DELAYS.get(action_type, 2)
        if RANDOM_DELAYS:
            return base * random.uniform(0.5, 1.5)
        return base

# ============ DRIVER MANAGER ============
class DriverManager:
    _port_counter = 9600
    _port_lock = threading.Lock()
    _driver_init_lock = threading.Lock()
    _browser_version_main = None
    _browser_executable_path = None
    
    @staticmethod
    def _get_next_port():
        with DriverManager._port_lock:
            port = DriverManager._port_counter
            DriverManager._port_counter += 1
            if DriverManager._port_counter > 9700:
                DriverManager._port_counter = 9600
            return port

    @staticmethod
    def _detect_browser_executable() -> Optional[str]:
        if DriverManager._browser_executable_path:
            return DriverManager._browser_executable_path
        try:
            browser_path = uc.find_chrome_executable()
            if browser_path and os.path.exists(browser_path):
                DriverManager._browser_executable_path = browser_path
        except Exception as e:
            pass
        return DriverManager._browser_executable_path

    @staticmethod
    def _detect_browser_version_main() -> Optional[int]:
        if DriverManager._browser_version_main is not None:
            return DriverManager._browser_version_main
        browser_path = DriverManager._detect_browser_executable()
        if not browser_path:
            return None
        if os.name == "nt":
            try:
                ps_command = f"(Get-Item '{browser_path}').VersionInfo.ProductVersion"
                result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], capture_output=True, text=True, timeout=5)
                match = re.search(r"(\d+)\.", result.stdout)
                if match:
                    DriverManager._browser_version_main = int(match.group(1))
            except:
                pass
        return DriverManager._browser_version_main

    @staticmethod
    def _build_options(thread_id: int = 0, total_workers: int = 1):
        options = uc.ChromeOptions()
        port = DriverManager._get_next_port()
        profile_dir = tempfile.mkdtemp(prefix=f"grok_auto_reg_{thread_id}_{port}_")
        if USE_ANTI_DETECT:
            user_agent = get_random_user_agent()
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # ── Smart Grid Layout ──
        # Tự động tính vị trí cửa sổ theo grid dựa trên thread_id
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Lấy kích thước màn hình thực (DPI-aware)
            user32.SetProcessDPIAware()
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)

            # Lấy WorkArea (trừ Taskbar)
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            rect = RECT()
            ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
            work_w = rect.right - rect.left
            work_h = rect.bottom - rect.top

            # Grid layout thông minh: tự động tính số cột dựa trên tổng số luồng
            # Ưu tiên chiều ngang hẹp để dễ theo dõi (narrow view)
            if total_workers <= 5:
                cols = total_workers if total_workers > 0 else 1
                rows_total = 1
            elif total_workers <= 10:
                cols = 5
                rows_total = 2
            else:
                # Nếu quá nhiều, chia tối đa 8 cột để giữ tính khả dụng
                cols = min(total_workers, 8)
                import math
                rows_total = math.ceil(total_workers / cols)

            col = thread_id % cols
            row = thread_id // cols

            win_w = work_w // cols
            win_h = work_h // rows_total
            pos_x = rect.left + col * win_w
            pos_y = rect.top  + row * win_h

            options.add_argument(f"--window-size={win_w},{win_h}")
            options.add_argument(f"--window-position={pos_x},{pos_y}")
        except Exception:
            # Fallback
            options.add_argument("--window-size=400,800")
            options.add_argument(f"--window-position={400 * (thread_id % 4)},0")
            
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--remote-debugging-port={port}")
        return options, profile_dir

    @staticmethod
    def create_driver(thread_id: int = 0, total_workers: int = 1):
        version_main = DriverManager._detect_browser_version_main()
        browser_path = DriverManager._detect_browser_executable()
        with DriverManager._driver_init_lock:
            try:
                options, profile_dir = DriverManager._build_options(thread_id, total_workers)
                driver = uc.Chrome(
                    options=options,
                    headless=False,
                    viewport=None,
                    version_main=version_main,
                    browser_executable_path=browser_path,
                    use_subprocess=True
                )
                driver._grok_profile_dir = profile_dir
                return driver
            except Exception as e:
                Logger.error(f"Cannot start browser: {e}")
                return None


# ============ GROK REGISTRATION ============
class GrokRegistration:
    def __init__(self):
        self.driver = None
        self.email = None
        self.password = DEFAULT_PASSWORD
        self.status = "not_started"
        self.page_detector = PageDetector()
        self.timing = TimingManager()
        self.thread_id = 0
        self.cookies = []

    def start(self, thread_id: int = 0, total_workers: int = 1) -> bool:
        self.thread_id = thread_id
        try:
            self.driver = DriverManager.create_driver(thread_id=thread_id, total_workers=total_workers)
            if self.driver is None: return False
            return True
        except Exception as e:
            Logger.error(f"Lỗi mở Chrome: {e}")
            return False

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except: pass
            if hasattr(self.driver, "_grok_profile_dir"):
                try: shutil.rmtree(self.driver._grok_profile_dir, ignore_errors=True)
                except: pass

    def _fast_fill_input(self, element, value: str):
        try: element.click()
        except: pass
        try: element.clear()
        except: pass

        for char in value:
            element.send_keys(char)
            # Giảm tốc độ gõ phím cho đều đặn hơn (100ms - 250ms)
            time.sleep(random.uniform(0.1, 0.2))
        return True

    def go_to_signup(self) -> bool:
        """Navigates to Grok sign-up and clicks 'Sign up with Email'"""
        try:
            self.driver.get("https://accounts.x.ai/sign-up?redirect=grok-com")
            # Bỏ wait_for_stable_state gây tốn 15s vô ích
            time.sleep(1.5)

            # Cập nhật XPath tìm bao gồm cả 'email' viết thường (thay vì chỉ 'Email' bị kẹt 15s Timeout ngớ ngẩn)
            btn_locator = (By.XPATH, "//button[contains(., '邮箱') or contains(translate(., 'EMAIL', 'email'), 'email')]")
            if not self.page_detector.wait_for_element_clickable(self.driver, btn_locator, 3):
                # Fallback JS search
                self.driver.execute_script("""
                    const btns = Array.from(document.querySelectorAll('button'));
                    const emailBtn = btns.find(b => b.innerText.includes('邮箱') || b.innerText.includes('Email') || b.querySelector('svg.lucide-mail'));
                    if (emailBtn) emailBtn.click();
                """)
            else:
                self.driver.find_element(*btn_locator).click()
            
            time.sleep(1)
            Logger.debug("Đã nhấn nút đăng ký bằng Email")
            return True
        except Exception as e:
            Logger.error(f"Navigation error: {e}")
            return False

    def enter_email(self, email: str) -> bool:
        self.email = email
        try:
            email_loc = (By.NAME, "email")
            if not self.page_detector.wait_for_element_present(self.driver, email_loc, 10):
                return False

            email_input = self.driver.find_element(*email_loc)
            self._fast_fill_input(email_input, email)

            time.sleep(1)
            # Find and click Sign Up button (注册)
            submit_loc = (By.XPATH, "//button[@type='submit' and (contains(., '注册') or contains(., 'Sign'))]")
            if self.page_detector.wait_for_element_clickable(self.driver, submit_loc, 5):
                self.driver.find_element(*submit_loc).click()
            else:
                self.driver.execute_script("document.querySelector('button[type=\"submit\"]').click()")
            
            Logger.debug("Đã nhập email và ấn submit")
            return True
        except Exception as e:
            Logger.error(f"Lỗi nhập email: {e}")
            return False

    def enter_verification_code(self, code: str) -> bool:
        try:
            code_loc = (By.NAME, "code")
            if not self.page_detector.wait_for_element_present(self.driver, code_loc, 15):
                return False
            
            code_input = self.driver.find_element(*code_loc)
            self._fast_fill_input(code_input, code)
            
            # X.ai tự động verify và nhảy trang ngay khi điền đủ 6 ký tự
            # KHÔNG bấm nút "Confirm" vì nếu delay, lệnh click có thể bấm nhầm vào Submit của trang Tên/Mật khẩu nhảy lên
            Logger.sub("Đã điền xong mã xác nhận, x.ai đang tự nhảy trang...")
            time.sleep(2)
            
            return True
        except Exception as e:
            Logger.error(f"Lỗi nhập code: {e}")
            return False

    def enter_name_password(self) -> bool:
        first_names = [
            "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
            "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
            "Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen",
            "Nancy", "Lisa", "Betty", "Margaret", "Sandra", "Ashley", "Kimberly", "Emily", "Donna", "Michelle",
            "Kevin", "Brian", "George", "Edward", "Ronald", "Timothy", "Jason", "Jeffrey", "Ryan", "Jacob"
        ]
        last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
            "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
            "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
            "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Baker", "Adams", "Nelson"
        ]
        g_name = random.choice(first_names)
        f_name = random.choice(last_names)

        try:
            if not self.page_detector.wait_for_element_present(self.driver, (By.NAME, "givenName"), 15):
                return False
            
            self._fast_fill_input(self.driver.find_element(By.NAME, "givenName"), g_name)
            self._fast_fill_input(self.driver.find_element(By.NAME, "familyName"), f_name)
            self._fast_fill_input(self.driver.find_element(By.NAME, "password"), self.password)
            Logger.sub(f"Tên: {g_name} {f_name}")
            return True
        except Exception as e:
            Logger.error(f"Lỗi điền tên/pass: {e}")
            return False

    def check_success(self) -> bool:
        """Kiểm tra thành công (Chỉ tin vào URL Dashboard hoặc Element đặc hữu)"""
        try:
            curr_url = self.driver.current_url.lower()
            # 1. Check URL (Đã nhảy trang và không còn ở sign-up)
            is_new_page = any(x in curr_url for x in ["grok.com", "/account", "/settings"]) and "sign-up" not in curr_url
            
            # 2. Check Element Dashboard (Nút Manage hoặc Sign-in methods)
            has_dashboard_element = self.driver.execute_script("""
                return document.body.innerText.includes('Manage your Grok') || 
                       document.body.innerText.includes('Sign-in methods') ||
                       !!document.querySelector('button[aria-label*="Account"]');
            """)

            if is_new_page or has_dashboard_element:
                if self.status != "success":
                    self.status = "success"
                    self.cookies = self.driver.get_cookies()
                return True
        except: pass
        return False

    def solve_cloudflare(self, timeout: int = 60) -> bool:
        """Tự động giải Cloudflare Turnstile (Smart Check)"""
        Logger.sub("🔎 Đang giám sát Cloudflare Turnstile...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Ưu tiên hàng đầu: Nếu đã vào Dashboard thì coi như xong luôn
            if self.check_success(): return True

            try:
                self.driver.switch_to.default_content()
                
                # Check Token
                token = self.driver.execute_script("return document.querySelector('[name=\"cf-turnstile-response\"]')?.value")
                if token and len(token) > 10:
                    Logger.sub("✅ Đã có Token Turnstile!")
                    return True

                # Tìm và click Turnstile qua frame index
                for i in range(8): # Quét 8 frame đầu
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(i)
                        if "challenges.cloudflare.com" in self.driver.current_url:
                            self.driver.execute_script("""
                                var el = document.elementFromPoint(30, 32) || document.querySelector('input');
                                if(el) {
                                    ['mousedown','mouseup','click'].forEach(t => {
                                        el.dispatchEvent(new MouseEvent(t, { bubbles: true, clientX: 30, clientY: 32 }));
                                    });
                                }
                            """)
                            Logger.sub(f"⚡ Đã click Turnstile (Frame #{i})")
                            self.driver.switch_to.default_content()
                            time.sleep(2)
                            break
                    except: break
                
                time.sleep(1.5)
            except:
                time.sleep(1)

        return self.check_success()

    def click_submit_button(self) -> bool:
        """Chuyên trách việc bấm nút Submit cuối"""
        try:
            Logger.sub("🚀 Đang gửi form đăng ký...")
            for attempt in range(3):
                if self.check_success(): return True
                
                # Cuộn xuống, tìm nút submit và bấm
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                submit_btn_loc = (By.XPATH, "//button[@type='submit' and not(@disabled)]")
                
                try:
                    if self.page_detector.wait_for_element_clickable(self.driver, submit_btn_loc, 2):
                        self.driver.find_element(*submit_btn_loc).click()
                        Logger.sub(f"Bấm nút Submit (Lần {attempt+1})")
                    else:
                        self.driver.execute_script("document.querySelector('button[type=\"submit\"]')?.click();")
                except: pass
                time.sleep(1.5)
            return True # Coi như đã bấm xong
        except Exception as e:
            Logger.error(f"Lỗi bấm nút Submit: {e}")
            return False

    def wait_for_dashboard_redirect(self, timeout: int = 20) -> bool:
        """Chuyên trách việc đợi và xác nhận nhảy trang thành công"""
        Logger.sub("⌛ Đang theo dõi tiến trình Redirect...")
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            if self.check_success():
                Logger.sub("🎉 Hệ thống xác nhận: ĐĂNG KÝ HOÀN TẤT!")
                return True
            time.sleep(1)
        
        return self.check_success()

    def get_account_data(self):
        return {
            "email": self.email,
            "password": self.password,
            "status": self.status,
            "cookies": self.cookies,
        }
