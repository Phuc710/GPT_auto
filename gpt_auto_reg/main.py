# main.py - ChatGPT Auto Registration
# Đăng ký tài khoản ChatGPT tự động với theo dõi từng bước

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
from gpt_selenium import GPTRegistration, SeleniumException
from step_tracker import StepTracker, Logger, Color


# ============ CONSTANTS ============
INFOACC_DIR  = "infoacc"
ACCOUNTS_CSV = "accounts.csv"

# Các bước đăng ký (key, label hiển thị)
REGISTRATION_STEPS = [
    ("email",    "Tạo email tạm thời"),
    ("browser",  "Mở trình duyệt"),
    ("signup",   "Đến trang đăng ký"),
    ("enter_email",    "Nhập email"),
    ("enter_password", "Nhập mật khẩu"),
    ("wait_code",      "Chờ mã xác minh"),
    ("enter_code",     "Nhập mã xác minh"),
    ("name_birthday",  "Nhập tên & ngày sinh"),
    ("verify",         "Kiểm tra kết quả"),
]


# ============ ACCOUNT STORAGE ============
class AccountStorage:
    """Lưu trữ tài khoản với cookies/tokens"""

    @staticmethod
    def ensure_dir():
        if not os.path.exists(INFOACC_DIR):
            os.makedirs(INFOACC_DIR)

    @staticmethod
    def save_csv(account_data: Dict[str, Any]) -> bool:
        """
        Lưu tài khoản vào accounts.csv.
        Các cột quan trọng từ session API:
          email, password, plan_type (plus/free),
          access_token (JWT), session_token, expires,
          user_id, account_id, created_at
        """
        COLUMNS = [
            "email", "password", "plan_type",
            "user_id", "account_id", "created_at",
            "session_token", "access_token",
        ]
        try:
            csv_exists = os.path.exists(ACCOUNTS_CSV)
            with open(ACCOUNTS_CSV, "a", newline="", encoding="utf-8") as f:
                if not csv_exists:
                    f.write("\ufeff")  # UTF-8 BOM cho Excel
                writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
                if not csv_exists:
                    writer.writeheader()

                writer.writerow({
                    "email":         account_data.get("email", ""),
                    "password":      account_data.get("password", ""),
                    "plan_type":     account_data.get("plan_type", ""),
                    "access_token":  account_data.get("access_token", ""),
                    "session_token": account_data.get("session_token", ""),
                    "user_id":       account_data.get("user_id", ""),
                    "account_id":    account_data.get("account_id", ""),
                    "created_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            return True
        except Exception as e:
            Logger.error(f"Lỗi lưu CSV: {e}")
            return False

    @staticmethod
    def save_individual(account_data: Dict[str, Any]) -> bool:
        """
        Luu tung tai khoan vao infoacc/<email>.json
        Bao gom: access_token, session_token, expires, user_id, account_id, plan_type, org_id, cookies
        """
        try:
            AccountStorage.ensure_dir()
            email     = account_data.get("email", "unknown")
            safe_name = email.replace("@", "_at_").replace(".", "_")
            filepath  = os.path.join(INFOACC_DIR, f"{safe_name}.json")
            save_data = {
                "email":          email,
                "password":       account_data.get("password", ""),
                "status":         account_data.get("status", "unknown"),
                "access_token":   account_data.get("access_token", ""),
                "session_token":  account_data.get("session_token", ""),
                "user_id":        account_data.get("user_id", ""),
                "account_id":     account_data.get("account_id", ""),
                "plan_type":      account_data.get("plan_type", ""),
                "org_id":         account_data.get("org_id", ""),
                "cookies":        account_data.get("cookies", []),
                "saved_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            Logger.error(f"Lỗi lưu JSON: {e}")
            return False

    @staticmethod
    def load_accounts_csv() -> List[Dict[str, Any]]:
        """Đọc danh sách tài khoản từ CSV"""
        accounts = []
        if not os.path.exists(ACCOUNTS_CSV):
            return accounts
        try:
            with open(ACCOUNTS_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    accounts.append(dict(row))
        except Exception as e:
            Logger.error(f"Lỗi đọc CSV: {e}")
        return accounts

    @staticmethod
    def delete_local_infoacc(email: str):
        """Xóa file JSON tạm nếu đăng ký lỗi (không bắt buộc nhưng giúp sạch thư mục)"""
        path = os.path.join(INFOACC_DIR, f"{email}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    @staticmethod
    def load_all_infoacc() -> List[Dict[str, Any]]:
        """Đọc tất cả tài khoản từ thư mục infoacc/"""
        accounts = []
        AccountStorage.ensure_dir()
        for filename in os.listdir(INFOACC_DIR):
            if not filename.endswith(".json"):
                continue
            filepath = os.path.join(INFOACC_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    accounts.append(json.load(f))
            except (json.JSONDecodeError, IOError):
                continue
        return accounts


# ============ REGISTRATION SERVICE ============
class RegistrationService:
    """Xử lý đăng ký ChatGPT với theo dõi từng bước"""

    def __init__(self):
        self.email_api: Optional[KaiMailAPI]      = None
        self.registration: Optional[GPTRegistration] = None

    # ---- Private helpers ----

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
        except Exception:
            pass

    # ---- Main registration ----

    def register_one(self, account_num: int = 1) -> Optional[Dict[str, Any]]:
        """Đăng ký 1 tài khoản ChatGPT với visual step tracker"""
        tracker = StepTracker(
            title=f"Đăng ký ChatGPT - Tài khoản #{account_num}",
            steps=REGISTRATION_STEPS,
        )
        tracker._draw()  # Hiển thị board ngay từ đầu

        email      = None
        account_data = None

        try:
            # ── Buoc 0: Tao email ──────────────────────────────────────
            tracker.start("email")
            if not self._create_email_api():
                tracker.fail("email", "Không khởi tạo được API")
                return self._finish(tracker, None, email=email)

            try:
                email = self.email_api.create_email()
            except KaiMailException as e:
                tracker.fail("email", str(e))
                return self._finish(tracker, None, email=email)

            if not email:
                tracker.fail("email", "Tạo email thất bại")
                return self._finish(tracker, None, email=email)

            tracker.done("email")
            Logger.sub(f"Email: {Color.CYAN}{email}{Color.RESET}")

            # ── Buoc 1: Mo trinh duyet ─────────────────────────────────
            tracker.start("browser")
            self.registration = GPTRegistration()
            if not self.registration.start():
                tracker.fail("browser", "Không thể mở Chrome")
                return self._finish(tracker, None, email=email)
            tracker.done("browser")

            # ── Buoc 2: Den trang dang ky ──────────────────────────────
            tracker.start("signup")
            if not self.registration.go_to_signup():
                tracker.fail("signup", "Không mở được trang đăng ký")
                return self._finish(tracker, None, email=email)
            tracker.done("signup")

            # ── Buoc 3: Nhap email ─────────────────────────────────────
            tracker.start("enter_email")
            if not self.registration.enter_email(email):
                tracker.fail("enter_email", "Không nhập được email")
                return self._finish(tracker, None, email=email)
            tracker.done("enter_email")

            # ── Buoc 4: Nhap mat khau ──────────────────────────────────
            tracker.start("enter_password")
            if not self.registration.enter_password():
                tracker.fail("enter_password", "Không nhập được mật khẩu")
                return self._finish(tracker, None, email=email)
            tracker.done("enter_password")

            # ── Buoc 5: Cho ma xac minh ────────────────────────────────
            tracker.start("wait_code")
            code = self.email_api.wait_for_openai_email(
                timeout=EMAIL_TIMEOUT,
                interval=CHECK_EMAIL_INTERVAL,
            )

            if not code:
                tracker.fail("wait_code", f"Hết {EMAIL_TIMEOUT}s, không nhận được mã")
                # Lưu pending để xử lý thủ công
                account_data = self.registration.get_account_data()
                account_data["status"]        = "pending_verification"
                account_data["email_service"] = "kaimail"
                AccountStorage.save_csv(account_data)
                return self._finish(tracker, account_data)

            tracker.done("wait_code")
            Logger.sub(f"Mã xác minh: {Color.CYAN}{code}{Color.RESET}")

            # ── Buoc 6: Nhap ma xac minh ──────────────────────────────
            tracker.start("enter_code")
            if not self.registration.enter_verification_code(code):
                tracker.fail("enter_code", "Không nhập được mã xác minh")
                return self._finish(tracker, None, email=email)
            tracker.done("enter_code")

            # ── Buoc 7: Nhap ten & ngay sinh ──────────────────────────
            tracker.start("name_birthday")
            self.registration.enter_name_birthday()
            tracker.done("name_birthday")

            # ── Buớc 8: Kiểm tra kết quả + lấy session ─────────────────
            tracker.start("verify")
            time.sleep(3)
            self.registration.check_success()

            # get_account_data() tự động gọi fetch_session() -> lấy accessToken + sessionToken
            account_data = self.registration.get_account_data()
            account_data["verification_code"] = code
            account_data["email_service"]     = "kaimail"

            # Luu CSV (Các cột đã cập nhật)
            AccountStorage.save_csv(account_data)

            # Lưu JSON (đầy đủ: access_token, session_token, expires, cookies...)
            AccountStorage.save_individual(account_data)

            has_token = bool(account_data.get("access_token"))
            Logger.sub(f"Access Token: {'Có' if has_token else 'Không có'}")
            Logger.sub(f"Plan: {account_data.get('plan_type', 'N/A')}")

            if account_data.get("status") == "success":
                tracker.done("verify")
            else:
                tracker.fail("verify", "Trang không đúng sau đăng ký")

            return self._finish(tracker, account_data)

        except SeleniumException as e:
            Logger.error(f"Lỗi Selenium: {e}")
            # Fail bước đang chạy
            for step in tracker.steps:
                if step.status.value == "running":
                    tracker.fail(step.name, str(e))
                    break
            return self._finish(tracker, None)
        except Exception as e:
            Logger.error(f"Lỗi không xác định: {e}")
            import traceback
            traceback.print_exc()
            return self._finish(tracker, None, email=email)

        finally:
            self._cleanup_browser()

    def _finish(self, tracker: StepTracker, account_data: Optional[Dict], email: Optional[str] = None) -> Optional[Dict]:
        """Hiển thị summary và trả về kết quả. Xóa email nếu thất bại."""
        success = False
        if account_data and account_data.get("status") == "success":
            success = True
            detail = (
                f"Email: {Color.CYAN}{account_data.get('email')}{Color.RESET}\n"
                f"     Mật khẩu: {account_data.get('password')}"
            )
            tracker.summary(success=True, detail=detail)
            return account_data
        
        # THẤT BẠI: Xóa email và dọn dẹp
        tracker.summary(success=False, detail="Đăng ký thất bại")
        
        # Ưu tiên lấy email từ account_data, nếu không có thì dùng tham số email
        target_email = (account_data.get("email") if account_data else None) or email
        
        if target_email and self.email_api:
            Logger.warning(f"Đang xóa email lỗi: {target_email}...")
            try:
                self.email_api.delete_email(target_email)
                AccountStorage.delete_local_infoacc(target_email)
            except Exception as e:
                Logger.debug(f"Không thể xóa email: {e}")
                
        return None


# ============ MENU HANDLERS ============

def handle_single_registration():
    """Option 1: Đăng ký 1 tài khoản"""
    service = RegistrationService()
    service.register_one(account_num=1)


def handle_parallel_registration():
    """Option 2: Đăng ký song song (nhiều browser cùng lúc)"""
    from parallel_register import ParallelRegistration

    Logger.section("ĐĂNG KÝ SONG SONG")

    try:
        raw = input("  Nhập số lượng tài khoản (1-10): ").strip()
        num = int(raw) if raw else 1
        if num < 1 or num > 10:
            Logger.warning("Số lượng phải từ 1 đến 10!")
            return
    except ValueError:
        Logger.warning("Vui lòng nhập số nguyên!")
        return

    parallel_reg = ParallelRegistration(num, 1920, 1080)
    results = parallel_reg.register_parallel(AccountStorage, Logger)
    Logger.success(f"Đã lưu {len(results)} tài khoản vào {INFOACC_DIR}/")


def view_csv_accounts():
    """Option 4: Xem tài khoản trong CSV"""
    accounts = AccountStorage.load_accounts_csv()
    W = 72
    print(f"\n{Color.BOLD}{'─' * W}")
    print(f"  DANH SÁCH TÀI KHOẢN  ({len(accounts)} tài khoản)")
    print(f"{'─' * W}{Color.RESET}")

    for acc in accounts:
        email     = acc.get("email", "N/A")
        password  = acc.get("password", "N/A")
        plan      = acc.get("plan_type", "?") or "?"
        created   = acc.get("created_at", "N/A")
        print(f"  {Color.GREEN}[✓]{Color.RESET} {email:<40} {plan_color}{plan.upper():<5}{Color.RESET}  {Color.GRAY}{created}{Color.RESET}")
        print(f"       {Color.DIM}Mật: {password}  |  Token: {has_tok}{Color.RESET}")

    print(f"{Color.BOLD}{'─' * W}{Color.RESET}\n")


def view_infoacc_accounts():
    """Option 5: Xem tài khoản trong infoacc/"""
    accounts = AccountStorage.load_all_infoacc()
    W = 62
    print(f"\n{Color.BOLD}{'─' * W}")
    print(f"  DANH SÁCH TÀI KHOẢN INFOACC/  ({len(accounts)} tài khoản)")
    print(f"{'─' * W}{Color.RESET}")

    for acc in accounts:
        status   = acc.get("status", "unknown")
        is_ok    = status == "success"
        color    = Color.GREEN if is_ok else Color.YELLOW
        icon     = "✓" if is_ok else "!"
        has_tok  = "KEY" if acc.get("access_token") else "---"
        has_ck   = "CK"  if acc.get("cookies") else "---"
        print(f"  {color}[{icon}]{Color.RESET} {acc.get('email', 'N/A')}")
        print(f"       {Color.GRAY}Token: {has_tok}  |  Cookies: {has_ck}  |  {acc.get('saved_at', 'N/A')}{Color.RESET}")

    print(f"{Color.BOLD}{'─' * W}{Color.RESET}\n")


# ============ MAIN ============

def display_menu():
    W = 62
    print(f"\n{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")
    print(f"  GPT AUTO REGISTRATION  |  v2.0")
    print(f"{Color.GRAY}{'─' * W}{Color.RESET}")
    print(f"  {Color.WHITE}1.{Color.RESET}  Đăng ký {Color.GREEN}1{Color.RESET} tài khoản")
    print(f"  {Color.WHITE}2.{Color.RESET}  Đăng ký {Color.GREEN}Parallel{Color.RESET}")
    print(f"  {Color.WHITE}3.{Color.RESET}  Xem tài khoản {Color.GRAY}(CSV){Color.RESET}")
    print(f"  {Color.WHITE}4.{Color.RESET}  Xem tài khoản {Color.GRAY}(infoacc/){Color.RESET}")
    print(f"  {Color.WHITE}0.{Color.RESET}  {Color.RED}Thoát{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")


def main():
    try:
        while True:
            display_menu()
            choice = input(f"  {Color.BOLD}>{Color.RESET} Chọn (0-4): ").strip()

            dispatch = {
                "1": handle_single_registration,
                "2": handle_parallel_registration,
                "3": view_csv_accounts,
                "4": view_infoacc_accounts,
            }

            if choice == "0":
                Logger.info("Tạm biệt!")
                break
            elif choice in dispatch:
                dispatch[choice]()
            else:
                Logger.warning("Lựa chọn không hợp lệ, chọn từ 0-4!")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n\n  {Color.YELLOW}Dừng bởi người dùng{Color.RESET}\n")
    except Exception as e:
        Logger.error(f"Lỗi không xác định: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
