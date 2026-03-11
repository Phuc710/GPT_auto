# gpt_selenium.py - Selenium automation for ChatGPT registration

import time
import sys
import random
import os
import shutil
from typing import Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from config import WAIT_TIME, DEFAULT_PASSWORD, USE_ANTI_DETECT, RANDOM_DELAYS, MIN_DELAY_MS, MAX_DELAY_MS
from anti_detect import get_random_user_agent, random_delay, random_scroll
from step_tracker import Logger  # Shared logger with colored output


# ============ EXCEPTION ============
class SeleniumException(Exception):
    """Custom exception for Selenium operations"""
    pass


# ============ PAGE DETECTOR ============
class PageDetector:
    """Detect page transitions and element presence"""
    
    @staticmethod
    def get_current_url(driver) -> str:
        """Safely get current URL"""
        try:
            return driver.current_url
        except Exception:
            return ""
    
    @staticmethod
    def get_page_title(driver) -> str:
        """Safely get page title"""
        try:
            return driver.title
        except Exception:
            return ""
    
    @staticmethod
    def wait_for_url_change(driver, old_url: str, timeout: int = 10) -> bool:
        """Wait for URL to change from old URL"""
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
    def wait_for_element_present(driver, locator: tuple, timeout: int = 10) -> bool:
        """Wait for element to be present in DOM"""
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False
    
    @staticmethod
    def wait_for_element_clickable(driver, locator: tuple, timeout: int = 10) -> bool:
        """Wait for element to be clickable"""
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.element_to_be_clickable(locator))
            return True
        except TimeoutException:
            return False
    
    @staticmethod
    def wait_for_element_hidden(driver, locator: tuple, timeout: int = 10) -> bool:
        """Wait for element to be hidden/removed"""
        try:
            wait = WebDriverWait(driver, timeout)
            wait.until(EC.invisibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False
    
    @staticmethod
    def is_url_changed(driver, old_url: str) -> bool:
        """Check if URL has changed"""
        try:
            return driver.current_url != old_url
        except Exception:
            return False
    
    @staticmethod
    def detect_page_type(driver) -> str:
        """Detect current page type based on URL and content"""
        url = driver.current_url.lower()
        
        if "chatgpt.com" in url and "auth" not in url:
            return "chat"
        elif "auth.openai.com" in url or "chatgpt.com/auth" in url:
            return "auth"
        elif "email-verification" in url:
            return "email_verification"
        elif "onboarding" in url or "welcome" in url:
            return "onboarding"
        elif "signup" in url or "register" in url:
            return "signup"
        else:
            return "unknown"


# ============ TIMING MANAGER ============
class TimingManager:
    """Manage adaptive timing based on page load"""
    
    # Base delays for different actions
    BASE_DELAYS = {
        "page_load": 3,
        "element_appear": 2,
        "after_click": 2,
        "form_submit": 3,
        "transition": 2,
    }
    
    @staticmethod
    def adaptive_delay(driver, base_delay: float = None) -> float:
        """Adaptive delay based on page readiness"""
        if base_delay is None:
            base_delay = TimingManager.BASE_DELAYS["page_load"]
        
        # Check if page is fully loaded
        try:
            ready_state = driver.execute_script("return document.readyState;")
            if ready_state == "complete":
                return base_delay
            else:
                # Page still loading, add extra time
                return base_delay + 2
        except Exception:
            return base_delay
    
    @staticmethod
    def wait_for_stable_state(driver, timeout: int = 10) -> bool:
        """Wait for page to reach stable state (network idle + DOM complete)"""
        start = time.time()
        last_url = ""
        stable_count = 0
        
        while time.time() - start < timeout:
            try:
                # Check URL stability
                current_url = driver.current_url
                
                # Check for network activity
                network_idle = driver.execute_script("""
                    return window.performance &&
                           window.performance.timing.loadEventEnd > 0 &&
                           (Date.now() - window.performance.timing.loadEventEnd) > 500;
                """)
                
                if current_url == last_url and network_idle:
                    stable_count += 1
                    if stable_count >= 2:  # Stable for 2 consecutive checks
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
        """Get appropriate delay for action type"""
        base = TimingManager.BASE_DELAYS.get(action_type, 2)
        
        if RANDOM_DELAYS:
            # Add random variation
            variation = random.uniform(0.5, 1.5)
            return base * variation
        return base


# ============ DRIVER MANAGER ============
class DriverManager:
    """Manage Chrome driver initialization"""
    
    _port_counter = 9500  # Starting port for multiple browsers
    _port_lock = None  # Will be initialized in create_driver
    
    @staticmethod
    def _get_next_port():
        """Get next available port for browser"""
        import threading
        if DriverManager._port_lock is None:
            DriverManager._port_lock = threading.Lock()
        
        with DriverManager._port_lock:
            port = DriverManager._port_counter
            DriverManager._port_counter += 1
            if DriverManager._port_counter > 9600:
                DriverManager._port_counter = 9500
            return port
    
    @staticmethod
    def create_driver(thread_id: int = 0):
        """Initialize undetected Chrome driver with anti-detection and unique port"""
        options = uc.ChromeOptions()
        
        # Use random User-Agent if anti-detect enabled
        if USE_ANTI_DETECT:
            user_agent = get_random_user_agent()
            Logger.info(f"Using random User-Agent")
        else:
            # Default fallback if anti-detect is disabled
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        
        options.add_argument(f"user-agent={user_agent}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1280,800")
        
        # Use unique port and user data dir for each thread to avoid conflicts
        port = DriverManager._get_next_port() + thread_id
        _home = os.path.expanduser("~")
        user_data_dir = os.path.join(_home, "AppData", "Local", "Google", "Chrome", "User Data", f"Profile_{port}")
        # Clear specific profile data before starting to ensure a fresh session
        if os.path.exists(user_data_dir):
            try:
                # Close any existing chrome processes that might be using this dir
                shutil.rmtree(user_data_dir, ignore_errors=True)
                Logger.info(f"Cleared browser profile: {port}")
            except Exception as e:
                Logger.warning(f"Could not clear profile: {e}")

        options.add_argument(f"--user-data-dir={user_data_dir}")
        options.add_argument(f"--remote-debugging-port={port}")
        
        # Proxy logic removed as per user request
        
        # Initialize driver
        try:
            driver = uc.Chrome(options=options, headless=False, version_main=144)
        except Exception as e:
            Logger.warning(f"Starting driver with older version: {e}")
            try:
                driver = uc.Chrome(options=options, headless=False)
            except Exception as e2:
                Logger.error(f"Cannot start browser: {e2}")
                return None
        
        return driver


# ============ GPT REGISTRATION ============
class GPTRegistration:
    """Handle ChatGPT registration with page detection and adaptive timing"""
    
    def __init__(self):
        self.driver = None
        self.email = None
        self.password = DEFAULT_PASSWORD
        self.status = "not_started"
        self.page_detector = PageDetector()
        self.timing = TimingManager()
        self.thread_id = 0
    
    def start(self, thread_id: int = 0) -> bool:
        """Start browser"""
        self.thread_id = thread_id
        try:
            Logger.info("Starting browser...")
            self.driver = DriverManager.create_driver(thread_id=thread_id)
            if self.driver is None:
                return False
            Logger.success("Trình duyệt đã sẵn sàng")
            return True
        except Exception as e:
            Logger.error(f"Cannot start browser: {e}")
            return False
    
    def go_to_signup(self) -> bool:
        """Navigate to ChatGPT and click Log in button"""
        try:
            # Extra safety: clear cookies and session storage before navigation
            try:
                self.driver.delete_all_cookies()
            except:
                pass

            Logger.sub("Đang điều hướng đến ChatGPT...")
            old_url = self.driver.current_url
            self.driver.get("https://chatgpt.com/")
            
            # Wait for page to be stable
            self.timing.wait_for_stable_state(self.driver)
            self.timing.adaptive_delay(self.driver, self.timing.get_action_delay("page_load"))
            
            # Random scroll if anti-detect enabled
            if USE_ANTI_DETECT:
                random_scroll(self.driver)
            
            wait = WebDriverWait(self.driver, WAIT_TIME)
            
            # Click "Log in" button
            try:
                # Try multiple selectors
                selectors = [
                    "button[data-testid='login-button']",
                    "a[href*='auth']",
                    "button"
                ]
                
                clicked = False
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if 'log in' in elem.text.lower():
                                elem.click()
                                clicked = True
                                break
                        if clicked:
                            break
                    except Exception:
                        continue
                
                if not clicked:
                    # JavaScript fallback
                    self.driver.execute_script("""
                        var buttons = document.querySelectorAll('button, a');
                        for(var i=0; i<buttons.length; i++){
                            if(buttons[i].textContent.trim().toLowerCase().includes('log in')){
                                buttons[i].click();
                                break;
                            }
                        }
                    """)
            except Exception as e:
                Logger.warning(f"Error clicking login: {e}")
                # Try JS fallback anyway
                self.driver.execute_script("""
                    var buttons = document.querySelectorAll('button, a');
                    for(var i=0; i<buttons.length; i++){
                        if(buttons[i].textContent.trim().toLowerCase().includes('log in')){
                            buttons[i].click();
                            break;
                        }
                    }
                """)
            
            Logger.debug("Clicked login button")
            
            # Wait for URL change (indicates navigation)
            time.sleep(self.timing.get_action_delay("after_click"))
            
            if not self.page_detector.wait_for_url_change(self.driver, old_url, timeout=10):
                Logger.debug("URL không đổi, có thể là modal popup")
            
            Logger.success("Đã chuyển đến trang đăng nhập")
            return True
            
        except TimeoutException:
            Logger.error("Page load timeout")
            return False
        except Exception as e:
            Logger.error(f"Navigation error: {e}")
            return False
    
    def enter_email(self, email: str) -> bool:
        """Enter email in the modal popup"""
        self.email = email
        wait = WebDriverWait(self.driver, WAIT_TIME)
        
        try:
            # Wait for email input to appear
            if not self.page_detector.wait_for_element_present(self.driver, (By.ID, "email"), timeout=10):
                Logger.error("Email input not found")
                return False
            
            time.sleep(self.timing.get_action_delay("element_appear"))
            
            # Find and clear email input
            email_input = self.driver.find_element(By.ID, "email")
            email_input.clear()
            
            # Type email character by character if anti-detect enabled
            if USE_ANTI_DETECT:
                from anti_detect import random_typing_delay
                for char in email:
                    email_input.send_keys(char)
                    random_typing_delay()
            else:
                email_input.send_keys(email)
            
            Logger.info(f"Đã nhập email: {email}")
            time.sleep(self.timing.get_action_delay("after_click"))
            
            # Click Continue button
            old_url = self.driver.current_url
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    self.driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for(var i=0; i<buttons.length; i++){
                            if(buttons[i].textContent.trim() === 'Continue'){
                                buttons[i].click();
                                break;
                            }
                        }
                    """)
                    Logger.debug(f"Attempt {attempt + 1}: Click Continue")
                    
                    # Wait and check if URL changed or password input appeared
                    time.sleep(self.timing.get_action_delay("transition"))
                    
                    # Check for password input (indicates success)
                    if self.page_detector.wait_for_element_present(
                        self.driver, (By.XPATH, "//input[@type='password']"), timeout=5
                    ):
                        Logger.success("Đã chuyển đến trang mật khẩu")
                        success = True
                        break
                    
                    # Check URL change
                    if self.page_detector.is_url_changed(self.driver, old_url):
                        Logger.success("URL changed, page transition successful")
                        success = True
                        break
                    
                    Logger.debug(f"Still on email page, retrying...")
                    
                except (StaleElementReferenceException, Exception) as e:
                    Logger.warning(f"Error clicking Continue: {e}")
                    time.sleep(1)
            
            if not success:
                Logger.error("Không thể chuyển đến trang mật khẩu")
            
            return success
            
        except TimeoutException:
            Logger.error("Email input not found")
            return False
        except Exception as e:
            Logger.error(f"Error entering email: {e}")
            return False
    
    def enter_password(self, password: str = None) -> bool:
        """Enter password on Create Account page"""
        if password:
            self.password = password
            
        try:
            # Wait for password input
            if not self.page_detector.wait_for_element_present(
                self.driver, (By.XPATH, "//input[@type='password']"), timeout=10
            ):
                Logger.error("Password input not found")
                return False
            
            time.sleep(self.timing.get_action_delay("element_appear"))
            
            # Find and clear password input
            password_input = self.driver.find_element(By.XPATH, "//input[@type='password']")
            password_input.clear()
            
            # Human-like typing
            if USE_ANTI_DETECT:
                from anti_detect import random_typing_delay
                for char in self.password:
                    password_input.send_keys(char)
                    random_typing_delay()
            else:
                password_input.send_keys(self.password)
                
            Logger.info("Đã nhập mật khẩu")
            time.sleep(self.timing.get_action_delay("after_click"))
            
            # Click Continue
            old_url = self.driver.current_url
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    self.driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for(var i=0; i<buttons.length; i++){
                            if(buttons[i].textContent.trim() === 'Continue'){
                                buttons[i].click();
                                break;
                            }
                        }
                    """)
                    Logger.debug(f"Attempt {attempt + 1}: Click Continue (password)")
                    
                    time.sleep(self.timing.get_action_delay("transition"))
                    
                    # Check for verification code input
                    code_locator = (By.XPATH, "//input[contains(@id, 'code') or @name='code' or contains(@placeholder, 'code')]")
                    if self.page_detector.wait_for_element_present(self.driver, code_locator, timeout=5):
                        Logger.success("Đã chuyển đến trang xác minh")
                        success = True
                        break
                    
                    # Check URL change
                    if self.page_detector.is_url_changed(self.driver, old_url):
                        current_page = self.page_detector.detect_page_type(self.driver)
                        Logger.success(f"Page changed (type: {current_page})")
                        success = True
                        break
                    
                    Logger.debug("Still on password page, retrying...")
                    
                except (StaleElementReferenceException, Exception) as e:
                    Logger.warning(f"Error clicking Continue: {e}")
                    time.sleep(1)
            
            if not success:
                Logger.error("Không thể chuyển đến trang xác minh")
            
            return success
            
        except TimeoutException:
            Logger.error("Password input not found")
            return False
        except Exception as e:
            Logger.error(f"Error entering password: {e}")
            return False
    
    def enter_verification_code(self, code: str) -> bool:
        """Enter 6-digit verification code"""
        try:
            # Wait for verification page
            time.sleep(self.timing.get_action_delay("page_load"))
            
            code_selectors = [
                "//input[@name='code']",
                "//input[@type='text']",
                "//input[contains(@placeholder, 'code')]",
                "//input[@maxlength='6']"
            ]
            
            for selector in code_selectors:
                try:
                    if not self.page_detector.wait_for_element_clickable(
                        self.driver, (By.XPATH, selector), timeout=5
                    ):
                        continue
                    
                    code_input = self.driver.find_element(By.XPATH, selector)
                    code_input.clear()
                    code_input.send_keys(code)
                    Logger.info(f"Đã nhập mã: {code}")
                    time.sleep(self.timing.get_action_delay("after_click"))
                    
                    # Click Continue
                    continue_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
                    continue_btn.click()
                    Logger.success("Đã nhấn Tiếp tục (xác minh)")
                    
                    # Wait for transition
                    time.sleep(self.timing.get_action_delay("transition"))
                    
                    self.status = "verified"
                    return True
                except (TimeoutException, NoSuchElementException):
                    continue
            
            Logger.error("Code input not found")
            return False
            
        except TimeoutException:
            Logger.error("Verification page timeout")
            return False
        except Exception as e:
            Logger.error(f"Error entering verification code: {e}")
            return False
    
    def enter_name_birthday(self) -> bool:
        """
        Enter random name + birthday, then click the final submit button.
        ChatGPT may use several button labels depending on the flow:
          - 'Continue'  (most common after verification)
          - 'Agree'     (terms agreement page)
          - 'Create account' / 'Get started' (final onboarding step)
        We try all of them with retries + fallback.
        """
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys

        first_names = ["John", "Tom", "Mike", "David", "James", "Robert",
                       "William", "Chris", "Daniel", "Matthew", "Andrew"]
        last_names  = ["Smith", "Johnson", "Williams", "Brown", "Jones",
                       "Miller", "Davis", "Wilson", "Taylor", "Anderson"]

        full_name   = f"{random.choice(first_names)} {random.choice(last_names)}"
        # Birth year (18-25 years old as requested)
        current_year = time.localtime().tm_year
        birth_year  = random.randint(current_year - 25, current_year - 18)
        birth_month = random.randint(1, 12)
        birth_day   = random.randint(1, 28)

        # All button labels ChatGPT might show at the final step
        FINAL_BUTTON_LABELS = [
            "Continue",
            "Agree",
            "Create account",
            "Get started",
            "Done",
            "Finish",
            "Finish creating account",
        ]

        try:
            time.sleep(self.timing.get_action_delay("page_load"))

            # ── Enter name ─────────────────────────────────────────────
            name_locators = [
                (By.CSS_SELECTOR, "input[name='name']"),
                (By.CSS_SELECTOR, "input[placeholder*='name']"),
                (By.CSS_SELECTOR, "input[id*='name']"),
                (By.CSS_SELECTOR, "input[type='text']"),
            ]
            name_input = None
            for locator in name_locators:
                if self.page_detector.wait_for_element_present(self.driver, locator, timeout=4):
                    name_input = self.driver.find_element(*locator)
                    break

            if name_input:
                name_input.clear()
                if USE_ANTI_DETECT:
                    from anti_detect import random_typing_delay
                    for ch in full_name:
                        name_input.send_keys(ch)
                        random_typing_delay()
                else:
                    name_input.send_keys(full_name)
                Logger.sub(f"Name: {full_name}")
            else:
                self.driver.execute_script(f"""
                    var inputs = document.querySelectorAll('input');
                    for(var i=0; i<inputs.length; i++){{
                        var ph = (inputs[i].placeholder || '').toLowerCase();
                        if(ph.includes('name') || inputs[i].type==='text'){{
                            inputs[i].value = '{full_name}';
                            inputs[i].dispatchEvent(new Event('input', {{bubbles:true}}));
                            break;
                        }}
                    }}
                """)
                Logger.sub(f"Name (JS): {full_name}")

            time.sleep(self.timing.get_action_delay("after_click"))

            # Use JavaScript for a more robust entry of the birthday
            # This handles both separate fields and single masked fields
            # We try to find any input, div or select that looks like birthday
            try:
                self.driver.execute_script(f"""
                    function fillBirthday(m, d, y) {{
                        const mStr = m.toString().padStart(2, '0');
                        const dStr = d.toString().padStart(2, '0');
                        const yStr = y.toString();

                        // Try separate fields by data-type (Radix/React UI)
                        const typeMap = {{'month': mStr, 'day': dStr, 'year': yStr}};
                        for (const [type, val] of Object.entries(typeMap)) {{
                            const el = document.querySelector(`div[data-type="${{type}}"][role="spinbutton"], input[name="${{type}}"], input[id*="${{type}}"]`);
                            if (el) {{
                                el.focus();
                                if (el.tagName === 'INPUT') {{
                                    el.value = val;
                                }} else {{
                                    el.innerText = val;
                                }}
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                            }}
                        }}

                        // Try combined input (DD/MM/YYYY or MM/DD/YYYY)
                        // Note: Some inputs are sensitive to character-by-character vs full string
                        const bdayInputs = document.querySelectorAll('input[type="text"][placeholder*="YYYY"], input[name*="birth"], input[id*="birth"]');
                        if (bdayInputs.length > 0) {{
                            const fullVal = `${{mStr}}${{dStr}}${{yStr}}`; // Try without slash first, or detect placeholder
                            bdayInputs.forEach(input => {{
                                input.focus();
                                // Clean existing
                                input.value = "";
                                // Use a simplified string if it's an auto-formatter
                                input.value = fullVal;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }});
                        }}
                    }}
                    fillBirthday({birth_month}, {birth_day}, {birth_year});
                """)
                Logger.info(f"Đã nhập ngày sinh: {birth_month:02d}/{birth_day:02d}/{birth_year}")
            except Exception as e:
                Logger.debug(f"JS birthday fill failed: {e}")
                
            # Fallback to ActionChains if JS didn't work or for additional stability
            for dtype, val in [("month", birth_month), ("day", birth_day), ("year", birth_year)]:
                try:
                    locators = [
                        (By.CSS_SELECTOR, f"div[data-type='{dtype}'][role='spinbutton']"),
                        (By.NAME, dtype),
                        (By.ID, dtype)
                    ]
                    for loc in locators:
                        try:
                            el = self.driver.find_element(*loc)
                            ac = ActionChains(self.driver)
                            ac.click(el).key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL)
                            ac.send_keys(Keys.BACKSPACE).send_keys(str(val)).perform()
                            break
                        except:
                            continue
                except:
                    pass

            Logger.sub(f"Birthday: {birth_month:02d}/{birth_day:02d}/{birth_year}")
            time.sleep(self.timing.get_action_delay("after_click"))

            # ── Click final button (aggressive - try every label) ───────
            old_url  = self.driver.current_url
            clicked  = False
            max_iter = 3

            for attempt in range(max_iter):
                # Try each known label
                for label in FINAL_BUTTON_LABELS:
                    try:
                        result = self.driver.execute_script(f"""
                            var btns = document.querySelectorAll('button');
                            for(var i=0; i<btns.length; i++){{
                                var txt = btns[i].textContent.trim();
                                if(txt === '{label}' && !btns[i].disabled){{
                                    btns[i].click();
                                    return '{label}';
                                }}
                            }}
                            return null;
                        """)
                        if result:
                            Logger.sub(f"Clicked: '{result}' (attempt {attempt+1})")
                            clicked = True
                            break
                    except Exception:
                        continue

                if not clicked:
                    # Last-resort: click first enabled submit/button that is visible
                    try:
                        self.driver.execute_script("""
                            var btns = document.querySelectorAll('button[type="submit"], button:not([disabled])');
                            for(var i=0; i<btns.length; i++){
                                var rect = btns[i].getBoundingClientRect();
                                if(rect.width > 0 && rect.height > 0){
                                    btns[i].click();
                                    break;
                                }
                            }
                        """)
                        Logger.debug(f"Clicked first visible button (fallback, attempt {attempt+1})")
                        clicked = True
                    except Exception:
                        pass

                if clicked:
                    # Wait and check if page moved on
                    time.sleep(self.timing.get_action_delay("transition"))
                    new_url = self.driver.current_url
                    if new_url != old_url:
                        Logger.sub(f"Page changed -> {new_url[:60]}")
                        break  # Success
                    # Page didn't change - maybe we need another click (multi-step onboarding)
                    old_url = new_url
                    clicked = False  # reset for next round

            self.status = "completed"
            return True

        except TimeoutException:
            Logger.error("Personal info page timeout")
            return False
        except Exception as e:
            Logger.error(f"Error entering name/birthday: {e}")
            return False
    
    def check_success(self) -> bool:
        """Check if registration was successful with page detection"""
        try:
            time.sleep(self.timing.get_action_delay("page_load"))

            page_type   = self.page_detector.detect_page_type(self.driver)
            current_url = self.driver.current_url
            Logger.debug(f"Current page type: {page_type} | {current_url[:60]}")

            # Explicit success pages
            if page_type in ("chat", "onboarding", "welcome"):
                self.status = "success"
                Logger.success("Đăng ký thành công!")
                return True

            # Broader: any chatgpt.com page that is NOT an error/auth page = likely success
            if "chatgpt.com" in current_url and "error" not in current_url:
                self.status = "success"
                Logger.success(f"Đã chuyển đến trang ChatGPT - Đánh dấu thành công")
                return True

            Logger.warning(f"Unexpected page after registration: {page_type}")
            return False

        except Exception as e:
            Logger.error(f"Error checking status: {e}")
            return False
    
    def fetch_session(self) -> dict:
        """
        Navigate to https://chatgpt.com/api/auth/session to retrieve:
          - accessToken  (JWT - use for API calls)
          - sessionToken (from cookie __Secure-next-auth.session-token)
          - user info (id, email)
          - account info (planType, organizationId)
          - expires
        Returns a dict with the extracted data (empty dict on failure).
        """
        SESSION_URL = "https://chatgpt.com/api/auth/session"
        try:
            Logger.sub(f"Đang lấy session từ {SESSION_URL}")
            self.driver.get(SESSION_URL)
            time.sleep(2)

            # The page renders JSON directly
            body = self.driver.find_element(By.TAG_NAME, "body").text
            import json as _json
            data = _json.loads(body)

            result = {
                "access_token":   data.get("accessToken", ""),
                "session_token":  data.get("sessionToken", ""),
                "expires":        data.get("expires", ""),
                "user_id":        data.get("user", {}).get("id", ""),
                "account_id":     data.get("account", {}).get("id", ""),
                "plan_type":      data.get("account", {}).get("planType", ""),
                "org_id":         data.get("account", {}).get("organizationId", ""),
            }
            Logger.sub(f"Session OK | plan={result['plan_type']} | expires={result['expires'][:10]}")
            return result

        except Exception as e:
            Logger.warning(f"fetch_session failed: {e}")
            # Fallback: extract session token from cookies
            try:
                cookies = self.driver.get_cookies()
                for c in cookies:
                    if c["name"] == "__Secure-next-auth.session-token":
                        return {"session_token": c["value"]}
            except Exception:
                pass
            return {}
    
    def get_account_data(self) -> dict:
        """
        Collect all account data after successful registration.
        Calls fetch_session() to get tokens from the session API.
        """
        session = {}
        try:
            session = self.fetch_session()
        except Exception:
            pass

        # Go back to chatgpt.com after fetching session
        try:
            if "chatgpt.com/api" in self.driver.current_url:
                self.driver.get("https://chatgpt.com/")
                time.sleep(1)
        except Exception:
            pass

        return {
            # Core info saved to CSV
            "email":         self.email,
            "password":      self.password,
            "status":        self.status,
            # Tokens saved to infoacc JSON
            "access_token":  session.get("access_token", ""),
            "session_token": session.get("session_token", ""),
            "expires":       session.get("expires", ""),
            "user_id":       session.get("user_id", ""),
            "account_id":    session.get("account_id", ""),
            "plan_type":     session.get("plan_type", ""),
            "org_id":        session.get("org_id", ""),
            "cookies":       self.driver.get_cookies() if self.driver else [],
        }
    
    def close(self):
        """Close browser"""
        try:
            if self.driver:
                self.driver.quit()
                Logger.info("Đã đóng trình duyệt")
        except Exception as e:
            Logger.warning(f"Error closing browser: {e}")


# ============ QUICK TEST ============
if __name__ == "__main__":
    print("Test GPT Registration with Page Detection...")
    reg = GPTRegistration()
    if reg.start():
        if reg.go_to_signup():
            print("OK Navigation successful!")
    print("\nClosing browser...")
    reg.close()
