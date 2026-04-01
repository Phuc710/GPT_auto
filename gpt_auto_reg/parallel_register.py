# parallel_register.py - Parallel registration module
# Called from main.py as option 2

import threading
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    EMAIL_TIMEOUT,
    CHECK_EMAIL_INTERVAL,
    KAIMAIL_BASE_URL,
    KAIMAIL_API_KEY,
    KAIMAIL_SECRET_KEY,
    KAIMAIL_DOMAIN,
    KAIMAIL_NAME_TYPE,
)
from kaimail_api import KaiMailAPI
from gpt_selenium import GPTRegistration, SeleniumException
from step_tracker import Logger, Color  # Shared colored logger


def get_screen_resolution():
    """Detect screen resolution using tkinter (cross-platform, built-in)"""
    try:
        import tkinter as tk
        root = tk.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    except Exception:
        # Fallback to standard HD if detection fails
        return 1920, 1080


class ScreenLayout:
    """Calculate browser window positions for parallel registration"""
    
    @staticmethod
    @staticmethod
    def calculate_positions(num_browsers: int, screen_width: int, screen_height: int) -> List[Dict[str, int]]:
        """
        Calculate optimal window positions for multiple browsers in a grid.
        Automatically decides columns and rows to maximize space.
        """
        positions = []
        
        # Decide grid structure
        if num_browsers <= 1:
            cols, rows = 1, 1
        elif num_browsers <= 2:
            cols, rows = 2, 1
        elif num_browsers <= 4:
            cols, rows = 2, 2
        elif num_browsers <= 6:
            cols, rows = 3, 2
        elif num_browsers <= 9:
            cols, rows = 3, 3
        else:
            # High count distribution
            cols = 4
            rows = (num_browsers + cols - 1) // cols

        # Reserve space for taskbar (approx 40-60px)
        usable_height = screen_height - 60
        
        cell_width = screen_width // cols
        cell_height = usable_height // rows
        
        gap = 5 # Small gap between windows

        for i in range(num_browsers):
            row = i // cols
            col = i % cols
            positions.append({
                "x": col * cell_width + gap,
                "y": row * cell_height + gap,
                "width": cell_width - (gap * 2),
                "height": cell_height - (gap * 2)
            })
        
        return positions


class ParallelRegistration:
    """Handle parallel registration with multiple browsers"""
    
    def __init__(self, num_accounts: int = 3, screen_width: int = None, screen_height: int = None):
        if screen_width is None or screen_height is None:
            detected_w, detected_h = get_screen_resolution()
            self.screen_width = screen_width or detected_w
            self.screen_height = screen_height or detected_h
        else:
            self.screen_width = screen_width
            self.screen_height = screen_height
            
        self.num_accounts = num_accounts
        self.positions = ScreenLayout.calculate_positions(num_accounts, self.screen_width, self.screen_height)
        self.results = []
        self.lock = threading.Lock()
    
    def _register_single(self, index: int, position: Dict[str, int], 
                         account_storage, logger) -> Optional[Dict[str, Any]]:
        """Register single account in a positioned browser window"""
        reg = None
        try:
            logger.info(f"[Thread-{index+1}] Bat dau dang ky...")
            
            # Create email via HMAC API
            email_api = KaiMailAPI(
                base_url=KAIMAIL_BASE_URL,
                api_key=KAIMAIL_API_KEY,
                secret_key=KAIMAIL_SECRET_KEY,
            )
            email = email_api.create_email()
            
            if not email:
                logger.error(f"[Thread-{index+1}] Tao email that bai")
                return None
            
            logger.success(f"[Thread-{index+1}] Email: {email}")
            
            # Create registration with positioned browser
            reg = GPTRegistration()
            if not reg.start(thread_id=index):
                raise SeleniumException("Khong the mo Chrome")
            
            # Position browser window
            try:
                reg.driver.set_window_position(position['x'], position['y'])
                reg.driver.set_window_size(position['width'], position['height'])
                logger.debug(f"[Thread-{index+1}] Window: ({position['x']}, {position['y']})")
            except Exception as e:
                logger.warning(f"[Thread-{index+1}] Khong the dat vi tri window: {e}")
            
            # Registration steps
            if not reg.go_to_signup():
                raise SeleniumException("Khong the mo trang dang ky")
            
            if not reg.enter_email(email):
                raise SeleniumException("Khong the nhap email")
            
            if not reg.enter_password():
                raise SeleniumException("Khong the nhap mat khau")
            
            # Wait for verification code
            code = email_api.wait_for_openai_email(
                timeout=EMAIL_TIMEOUT,
                interval=CHECK_EMAIL_INTERVAL
            )
            
            if not code:
                logger.warning(f"[Thread-{index+1}] Khong co ma xac minh - luu de xac minh thu cong")
                account_data = reg.get_account_data()
                account_data['status'] = 'pending_verification'
                account_data['email_service'] = 'kaimail'
                account_storage.save_individual(account_data)
                account_storage.save_csv(account_data)
                reg.close()
                return account_data
            
            if not reg.enter_verification_code(code):
                raise SeleniumException("Khong the nhap ma xac minh")
            
            reg.enter_name_birthday()
            time.sleep(3)
            reg.check_success()
            
            # Get and save account data
            account_data = reg.get_account_data()
            account_data['verification_code'] = code
            account_data['email_service'] = 'kaimail'
            
            account_storage.save_individual(account_data)
            account_storage.save_csv(account_data)
            
            logger.success(f"[Thread-{index+1}] Hoan thanh: {email}")
            
            time.sleep(5)
            reg.close()
            
            return account_data
            
        except Exception as e:
            logger.error(f"[Thread-{index+1}] Loi: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            if reg:
                try:
                    reg.close()
                except:
                    pass
            # Always try to delete the temporary email after use
            is_success = False
            if 'account_data' in locals() and account_data and account_data.get('status') == 'success':
                is_success = True

            if email and email_api:
                if not is_success:
                    try:
                        logger.warning(f"[Thread-{index+1}] Dang xoa email tam thoi do loi (Cleanup): {email}...")
                        email_api.delete_email(email)
                    except Exception as e:
                        logger.debug(f"[Thread-{index+1}] Khong the xoa email: {e}")
                else:
                    logger.info(f"[Thread-{index+1}] Done Mail: {email}")
    
    def register_parallel(self, account_storage, logger) -> List[Dict[str, Any]]:
        """Register multiple accounts in parallel"""
        W = 62
        print(f"\n{Color.BOLD}{'=' * W}")
        print(f"  DANG KY SONG SONG  |  {self.num_accounts} tai khoan")
        print(f"  Man hinh: {self.screen_width}x{self.screen_height}")
        print(f"{'=' * W}{Color.RESET}")

        # Show window layout
        print(f"\n{Color.GRAY}  Bo cuc cua so:{Color.RESET}")
        for i, pos in enumerate(self.positions):
            print(f"  {Color.CYAN}Browser {i+1}:{Color.RESET} ({pos['x']}, {pos['y']})  {pos['width']}x{pos['height']}")
        print()
        
        # Start parallel registration
        with ThreadPoolExecutor(max_workers=self.num_accounts) as executor:
            futures = []
            for i in range(self.num_accounts):
                # Delay 0.5s giua moi thread de tranh conflict chromedriver
                if i > 0:
                    logger.info(f"Cho 0.5s truoc khi mo browser tiep theo...")
                    time.sleep(0.5)
                
                future = executor.submit(
                    self._register_single, i, self.positions[i], 
                    account_storage, logger
                )
                futures.append(future)
            
            # Wait for all to complete
            for future in as_completed(futures):
                result = future.result()
                if result:
                    with self.lock:
                        self.results.append(result)
        
        # Summary
        W = 62
        done_count = len(self.results)
        print(f"\n{Color.BOLD}{'=' * W}")
        if done_count == self.num_accounts:
            print(f"  {Color.GREEN}✓  HOAN THANH SONG SONG{Color.RESET}{Color.BOLD}")
        else:
            print(f"  {Color.YELLOW}⚠  HOAN THANH (co loi){Color.RESET}{Color.BOLD}")
        print(f"{'─' * W}{Color.RESET}")
        print(f"  {Color.GRAY}Ket qua: {done_count}/{self.num_accounts} thanh cong{Color.RESET}")
        print()

        for i, acc in enumerate(self.results):
            is_ok  = acc.get("status") == "success"
            icon   = f"{Color.GREEN}✓{Color.RESET}" if is_ok else f"{Color.YELLOW}!{Color.RESET}"
            print(f"  [{icon}] {acc.get('email')}")
            print(f"       {Color.GRAY}Pass: {acc.get('password')}{Color.RESET}")

        print(f"{Color.BOLD}{'=' * W}{Color.RESET}")
        return self.results
