# grok_main.py - Grok Auto Registration
# Đăng ký tài khoản Grok tự động với theo dõi từng bước

import csv
import json
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import (
    DEFAULT_PASSWORD,
    EMAIL_TIMEOUT,
    CHECK_EMAIL_INTERVAL,
    KAIMAIL_BASE_URL,
    KAIMAIL_API_KEY,
    KAIMAIL_SECRET_KEY,
)
from kaimail_api import KaiMailAPI, KaiMailException
from grok_selenium import GrokRegistration, SeleniumException
from step_tracker import StepTracker, Logger, Color


# ============ CONSTANTS ============
REGISTRATION_STEPS = [
    ("email",    "Tạo email tạm thời (Kaimail)"),
    ("browser",  "Mở trình duyệt"),
    ("signup",   "Đến trang đăng ký x.ai"),
    ("enter_email",    "Nhập email & Submit"),
    ("wait_code",      "Chờ mã xác minh (OTP)"),
    ("enter_code",     "Nhập mã xác minh"),
    ("name_password",  "Nhập tên & mật khẩu"),
    ("cloudflare",     "Bypass Cloudflare Turnstile"),
    ("submit_signup",  "Nhấn nút Complete sign up"),
    ("redirect",       "Redirect & Chốt tài khoản"),
]





# ============ REGISTRATION SERVICE ============
class RegistrationService:
    def __init__(self):
        self.email_api: Optional[KaiMailAPI]      = None
        self.registration: Optional[GrokRegistration] = None

    def _create_email_api(self) -> bool:
        try:
            self.email_api = KaiMailAPI(
                base_url=KAIMAIL_BASE_URL,
                api_key=KAIMAIL_API_KEY,
                secret_key=KAIMAIL_SECRET_KEY,
            )
            return True
        except Exception as e:
            Logger.error(f"Lỗi khởi tạo KaiMail API: {e}")
            return False

    def _cleanup_browser(self):
        try:
            if self.registration:
                self.registration.close()
        except:
            pass

    def register_one(self, account_num: int = 1, thread_id: int = 0, total_workers: int = 1) -> Optional[Dict[str, Any]]:
        tracker = StepTracker(
            title=f"Đăng ký Grok (x.ai) - Tài khoản #{account_num}",
            steps=REGISTRATION_STEPS,
        )
        tracker._draw()

        email = None
        account_data = None

        try:
            # Bước 0: Tạo email
            tracker.start("email")
            if not self._create_email_api():
                tracker.fail("email", "Không khởi tạo được API")
                return self._finish(tracker, None, email)
            email = self.email_api.create_email()
            if not email:
                tracker.fail("email", "Tạo email thất bại")
                return self._finish(tracker, None, email)
            tracker.done("email")
            Logger.sub(f"Email: {Color.CYAN}{email}{Color.RESET}")

            # Bước 1: Mở trình duyệt
            tracker.start("browser")
            self.registration = GrokRegistration()
            if not self.registration.start(thread_id=thread_id, total_workers=total_workers):
                tracker.fail("browser", "Không thể mở Chrome")
                return self._finish(tracker, None, email)
            tracker.done("browser")

            # Bước 2: Đến trang đăng ký
            tracker.start("signup")
            if not self.registration.go_to_signup():
                tracker.fail("signup", "Không mở được trang đăng ký")
                return self._finish(tracker, None, email)
            tracker.done("signup")

            # Bước 3: Nhập email
            tracker.start("enter_email")
            if not self.registration.enter_email(email):
                tracker.fail("enter_email", "Không nhập được email")
                return self._finish(tracker, None, email)
            tracker.done("enter_email")

            # Bước 4: Chờ mã xác minh
            tracker.start("wait_code")
            # Wait for x.ai email (KaiMail API uses openai/chatgpt check inside `wait_for_openai_email`...)
            # We override that behavior here manually by polling `get_messages` for our custom need if original API only looks for openai
            start_time = time.time()
            code = None
            while time.time() - start_time < EMAIL_TIMEOUT:
                msgs = self.email_api.get_messages()
                for m in msgs:
                    # Look for verification code in emails for x.ai
                    b_txt = m.get("subject", "") + " "
                    # Try to extract 6 character code (e.g. GDT-Z6T)
                    import re
                    match = re.search(r"\b([A-Za-z0-9]{3}-?[A-Za-z0-9]{3})\b", b_txt)
                    if not match:
                        if m.get("id"):
                            detail = self.email_api.get_message_detail(m["id"])
                            if detail:
                                b_txt += (detail.get("body_text") or "")
                                match = re.search(r"\b([A-Za-z0-9]{3}-?[A-Za-z0-9]{3})\b", b_txt)
                    if match:
                        code = match.group(1).replace("-", "")
                        break
                if code: break
                time.sleep(CHECK_EMAIL_INTERVAL)

            if not code:
                tracker.fail("wait_code", f"Hết {EMAIL_TIMEOUT}s, không nhận được mã")
                account_data = self.registration.get_account_data()
                account_data["status"] = "pending_verification"
                return self._finish(tracker, account_data, email)
            tracker.done("wait_code")
            Logger.sub(f"Mã xác minh: {Color.CYAN}{code}{Color.RESET}")

            # Bước 5: Nhập mã xác minh
            tracker.start("enter_code")
            if not self.registration.enter_verification_code(code):
                tracker.fail("enter_code", "Không nhập được mã xác minh")
                return self._finish(tracker, None, email)
            tracker.done("enter_code")

            # Bước 6: Nhập Tên / MK
            tracker.start("name_password")
            if not self.registration.enter_name_password():
                tracker.fail("name_password", "Không điền được Info")
                return self._finish(tracker, None, email)
            tracker.done("name_password")

            # Bước 7: Cloudflare Turnstile Bypass
            tracker.start("cloudflare")
            if not self.registration.solve_cloudflare():
                tracker.fail("cloudflare", "Không click được Cloudflare")
                return self._finish(tracker, None, email)
            tracker.done("cloudflare")

            # Bước 8: Nhấn nút ấn định đăng ký
            tracker.start("submit_signup")
            if not self.registration.click_submit_button():
                tracker.fail("submit_signup", "Không bấm được nút Submit")
                return self._finish(tracker, None, email)
            tracker.done("submit_signup")

            # Bước 9: Đợi nhảy trang Dashboard
            tracker.start("redirect")
            if not self.registration.wait_for_dashboard_redirect():
                tracker.fail("redirect", "Không nhảy sang trang Dashboard")
                return self._finish(tracker, None, email)
            tracker.done("redirect")

            # Hoàn thành
            account_data = self.registration.get_account_data()
            return self._finish(tracker, account_data, email)

        except Exception as e:
            Logger.error(f"Lỗi không xác định: {e}")
            for step in tracker.steps:
                if step.status.value == "running":
                    tracker.fail(step.name, str(e))
                    break
            return self._finish(tracker, None, email)

        finally:
            self._cleanup_browser()

    def _finish(self, tracker, account_data, email=None):
        success = False
        if account_data and account_data.get("status") == "success":
            success = True
            detail = f"Email: {Color.CYAN}{account_data.get('email')}{Color.RESET}\n     Mật khẩu: {account_data.get('password')}"
            tracker.summary(success=True, detail=detail)
        else:
            tracker.summary(success=False, detail="Đăng ký thất bại")
        
        target_email = (account_data.get("email") if account_data else None) or email
        if target_email and self.email_api:
            if not success:
                Logger.info(f"Đang dọn dẹp email lỗi: {target_email}")
                try: self.email_api.delete_email(target_email)
                except: pass
        return account_data

def display_menu():
    W = 62
    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")
    print(f"  GROK (X.AI) AUTO REGISTRATION  |  v1.0")
    print(f"{Color.GRAY}{'─' * W}{Color.RESET}")
    print(f"  {Color.WHITE}1.{Color.RESET}  Đăng ký {Color.GREEN}1{Color.RESET} tài khoản Grok")
    print(f"  {Color.WHITE}2.{Color.RESET}  Đăng ký {Color.YELLOW}NHIỀU{Color.RESET} tài khoản {Color.CYAN}(Multi-thread){Color.RESET}")
    print(f"  {Color.WHITE}0.{Color.RESET}  {Color.RED}Thoát{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")


# ============ PARALLEL REGISTRATION ============
import threading

_results_lock = threading.Lock()
_results: list[dict] = []
_counters = {"success": 0, "failed": 0, "running": 0}

def _worker(account_num: int, slot_id: int, total_workers: int):
    """Mỗi thread chạy độc lập: Chrome riêng, Tracker riêng, vị trí cửa sổ riêng"""
    with _results_lock:
        _counters["running"] += 1

    service = RegistrationService()
    result = service.register_one(account_num=account_num, thread_id=slot_id, total_workers=total_workers)

    with _results_lock:
        _counters["running"] -= 1
        if result and result.get("status") == "success":
            _counters["success"] += 1
            _results.append(result)
        else:
            _counters["failed"] += 1

def run_parallel(total: int):
    """Chạy nhiều tài khoản song song - tự động tính luồng & layout cửa sổ"""
    # Không giới hạn luồng, chạy toàn bộ số lượng yêu cầu song song
    max_workers = total
    W = 62
    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")
    print(f"  🚀 ĐĂNG KÝ {Color.GREEN}{total}{Color.RESET} TÀI KHOẢN | "
          f"{Color.YELLOW}TẤT CẢ CHẠY SONG SONG{Color.RESET}")
    print(f"{Color.GRAY}{'─' * W}{Color.RESET}\n")

    semaphore = threading.Semaphore(max_workers)
    threads: list[threading.Thread] = []

    _slot_counter = 0
    _slot_lock = threading.Lock()

    def guarded_worker(num):
        nonlocal _slot_counter
        with semaphore:
            with _slot_lock:
                slot = _slot_counter
                _slot_counter += 1
            _worker(num, slot, total)

    for i in range(1, total + 1):
        t = threading.Thread(target=guarded_worker, args=(i,), daemon=True)
        threads.append(t)
        t.start()
        time.sleep(2.0)  # Stagger để tránh race condition ChromeDriver

    for t in threads:
        t.join()

    # === Tổng kết ===
    print(f"\n{Color.BOLD}{'═' * W}{Color.RESET}")
    print(f"  📊 KẾT QUẢ CUỐI CÙNG")
    print(f"{Color.GRAY}{'─' * W}{Color.RESET}")
    print(f"  ✅ Thành công : {Color.GREEN}{_counters['success']}{Color.RESET}")
    print(f"  ❌ Thất bại   : {Color.RED}{_counters['failed']}{Color.RESET}")
    print(f"  📋 Tổng cộng  : {total}")
    print(f"{Color.GRAY}{'─' * W}{Color.RESET}")

    if _results:
        print(f"\n  {Color.CYAN}📁 DANH SÁCH TÀI KHOẢN THÀNH CÔNG:{Color.RESET}")
        for i, acc in enumerate(_results, 1):
            print(f"  {Color.GREEN}{i:>3}.{Color.RESET} {acc['email']} | {acc['password']}")

        out_file = os.path.join(os.path.dirname(__file__), "accounts.csv")
        write_header = not os.path.exists(out_file)
        try:
            import csv as _csv
            with open(out_file, "a", newline="", encoding="utf-8") as f:
                writer = _csv.DictWriter(f, fieldnames=["email", "password", "status"])
                if write_header:
                    writer.writeheader()
                for acc in _results:
                    writer.writerow({
                        "email": acc.get("email", ""),
                        "password": acc.get("password", ""),
                        "status": acc.get("status", ""),
                    })
            print(f"\n  {Color.GREEN}💾 Đã lưu vào: {Color.CYAN}{out_file}{Color.RESET}")
        except Exception as e:
            Logger.error(f"Lỗi ghi CSV: {e}")

    print(f"{Color.BOLD}{'═' * W}{Color.RESET}\n")


def main():
    try:
        while True:
            display_menu()
            choice = input(f"  {Color.BOLD}>{Color.RESET} Chọn (0-2): ").strip()
            if choice == "0":
                break
            if choice == "1":
                service = RegistrationService()
                service.register_one()
            elif choice == "2":
                try:
                    n = int(input(f"  {Color.BOLD}>{Color.RESET} Số tài khoản muốn đăng ký: ").strip())
                    if n < 1:
                        Logger.error("Số lượng phải >= 1")
                        continue
                    _results.clear()
                    _counters.update({"success": 0, "failed": 0, "running": 0})
                    run_parallel(total=n)
                except ValueError:
                    Logger.error("Vui lòng nhập số nguyên hợp lệ")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
