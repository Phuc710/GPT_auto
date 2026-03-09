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
    ("email",    "Tao email tam thoi"),
    ("browser",  "Mo trinh duyet"),
    ("signup",   "Den trang dang ky"),
    ("enter_email",    "Nhap email"),
    ("enter_password", "Nhap mat khau"),
    ("wait_code",      "Cho ma xac minh"),
    ("enter_code",     "Nhap ma xac minh"),
    ("name_birthday",  "Nhap ten & ngay sinh"),
    ("verify",         "Kiem tra ket qua"),
]


# ============ ACCOUNT STORAGE ============
class AccountStorage:
    """Luu tru tai khoan voi cookies/tokens"""

    @staticmethod
    def ensure_dir():
        if not os.path.exists(INFOACC_DIR):
            os.makedirs(INFOACC_DIR)

    @staticmethod
    def save_csv(account_data: Dict[str, Any]) -> bool:
        """Luu tai khoan vao accounts.csv - bao gom full session data (khong co status)"""
        COLUMNS = [
            "email", "password", "access_token", "session_token", 
            "expires", "user_id", "account_id", "plan_type", "org_id", "created_at"
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
                    "access_token":  account_data.get("access_token", ""),
                    "session_token": account_data.get("session_token", ""),
                    "expires":       account_data.get("expires", ""),
                    "user_id":       account_data.get("user_id", ""),
                    "account_id":    account_data.get("account_id", ""),
                    "plan_type":     account_data.get("plan_type", ""),
                    "org_id":        account_data.get("org_id", ""),
                    "created_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
            return True
        except Exception as e:
            Logger.error(f"Loi luu CSV: {e}")
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
                "expires":        account_data.get("expires", ""),
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
            Logger.error(f"Loi luu JSON: {e}")
            return False

    @staticmethod
    def load_accounts_csv() -> List[Dict[str, Any]]:
        """Doc danh sach tai khoan tu CSV"""
        accounts = []
        if not os.path.exists(ACCOUNTS_CSV):
            return accounts
        try:
            with open(ACCOUNTS_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    accounts.append(dict(row))
        except Exception as e:
            Logger.error(f"Loi doc CSV: {e}")
        return accounts

    @staticmethod
    def load_all_infoacc() -> List[Dict[str, Any]]:
        """Doc tat ca tai khoan tu thu muc infoacc/"""
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
    """Xu ly dang ky ChatGPT voi theo doi tung buoc"""

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
            Logger.error(f"Loi khoi tao KaiMail API: {e}")
            return False

    def _cleanup_browser(self):
        try:
            if self.registration:
                self.registration.close()
        except Exception:
            pass

    # ---- Main registration ----

    def register_one(self, account_num: int = 1) -> Optional[Dict[str, Any]]:
        """Dang ky 1 tai khoan ChatGPT voi visual step tracker"""
        tracker = StepTracker(
            title=f"Dang ky ChatGPT - Tai khoan #{account_num}",
            steps=REGISTRATION_STEPS,
        )
        tracker._draw()  # Hien thi board ngay tu dau

        email      = None
        account_data = None

        try:
            # ── Buoc 0: Tao email ──────────────────────────────────────
            tracker.start("email")
            if not self._create_email_api():
                tracker.fail("email", "Khong khoi tao duoc API")
                return self._finish(tracker, None)

            try:
                email = self.email_api.create_email()
            except KaiMailException as e:
                tracker.fail("email", str(e))
                return self._finish(tracker, None)

            if not email:
                tracker.fail("email", "Tao email that bai")
                return self._finish(tracker, None)

            tracker.done("email")
            Logger.sub(f"Email: {Color.CYAN}{email}{Color.RESET}")

            # ── Buoc 1: Mo trinh duyet ─────────────────────────────────
            tracker.start("browser")
            self.registration = GPTRegistration()
            if not self.registration.start():
                tracker.fail("browser", "Khong the mo Chrome")
                return self._finish(tracker, None)
            tracker.done("browser")

            # ── Buoc 2: Den trang dang ky ──────────────────────────────
            tracker.start("signup")
            if not self.registration.go_to_signup():
                tracker.fail("signup", "Khong mo duoc trang dang ky")
                return self._finish(tracker, None)
            tracker.done("signup")

            # ── Buoc 3: Nhap email ─────────────────────────────────────
            tracker.start("enter_email")
            if not self.registration.enter_email(email):
                tracker.fail("enter_email", "Khong nhap duoc email")
                return self._finish(tracker, None)
            tracker.done("enter_email")

            # ── Buoc 4: Nhap mat khau ──────────────────────────────────
            tracker.start("enter_password")
            if not self.registration.enter_password():
                tracker.fail("enter_password", "Khong nhap duoc mat khau")
                return self._finish(tracker, None)
            tracker.done("enter_password")

            # ── Buoc 5: Cho ma xac minh ────────────────────────────────
            tracker.start("wait_code")
            code = self.email_api.wait_for_openai_email(
                timeout=EMAIL_TIMEOUT,
                interval=CHECK_EMAIL_INTERVAL,
            )

            if not code:
                tracker.fail("wait_code", f"Het {EMAIL_TIMEOUT}s, khong nhan duoc ma")
                # Luu pending de xu ly thu cong
                account_data = self.registration.get_account_data()
                account_data["status"]        = "pending_verification"
                account_data["email_service"] = "kaimail"
                AccountStorage.save_csv(account_data)
                return self._finish(tracker, account_data)

            tracker.done("wait_code")
            Logger.sub(f"Ma xac minh: {Color.CYAN}{code}{Color.RESET}")

            # ── Buoc 6: Nhap ma xac minh ──────────────────────────────
            tracker.start("enter_code")
            if not self.registration.enter_verification_code(code):
                tracker.fail("enter_code", "Khong nhap duoc ma xac minh")
                return self._finish(tracker, None)
            tracker.done("enter_code")

            # ── Buoc 7: Nhap ten & ngay sinh ──────────────────────────
            tracker.start("name_birthday")
            self.registration.enter_name_birthday()
            tracker.done("name_birthday")

            # ── Buoc 8: Kiem tra ket qua + lay session ─────────────────
            tracker.start("verify")
            time.sleep(3)
            self.registration.check_success()

            # get_account_data() tu dong goi fetch_session() -> lay accessToken + sessionToken
            account_data = self.registration.get_account_data()
            account_data["verification_code"] = code
            account_data["email_service"]     = "kaimail"

            # Luu CSV (4 cot chuan: email, password, status, created_at)
            AccountStorage.save_csv(account_data)

            # Luu JSON (day du: access_token, session_token, expires, cookies...)
            AccountStorage.save_individual(account_data)

            has_token = bool(account_data.get("access_token"))
            Logger.sub(f"Access Token: {'Co' if has_token else 'Khong co'}")
            Logger.sub(f"Plan: {account_data.get('plan_type', 'N/A')}")

            if account_data.get("status") == "success":
                tracker.done("verify")
            else:
                tracker.fail("verify", "Trang khong dung sau dang ky")

            return self._finish(tracker, account_data)

        except SeleniumException as e:
            Logger.error(f"Loi Selenium: {e}")
            # Fail buoc dang chay
            for step in tracker.steps:
                if step.status.value == "running":
                    tracker.fail(step.name, str(e))
                    break
            return self._finish(tracker, None)

        except Exception as e:
            Logger.error(f"Loi khong xac dinh: {e}")
            import traceback
            traceback.print_exc()
            return self._finish(tracker, None)

        finally:
            self._cleanup_browser()

    def _finish(self, tracker: StepTracker, account_data: Optional[Dict]) -> Optional[Dict]:
        """Hien thi summary va tra ve ket qua"""
        if account_data:
            status = account_data.get("status", "unknown")
            if status == "success":
                detail = (
                    f"Email: {Color.CYAN}{account_data.get('email')}{Color.RESET}\n"
                    f"     Password: {account_data.get('password')}"
                )
                tracker.summary(success=True, detail=detail)
            else:
                tracker.summary(success=False, detail=f"Trang thai: {status}")
        else:
            tracker.summary(success=False, detail="Dang ky that bai hoan toan")
        return account_data


# ============ MENU HANDLERS ============

def handle_single_registration():
    """Option 1: Dang ky 1 tai khoan"""
    service = RegistrationService()
    service.register_one(account_num=1)


def handle_parallel_registration():
    """Option 2: Dang ky song song (nhieu browser cung luc)"""
    from parallel_register import ParallelRegistration

    Logger.section("DANG KY SONG SONG")

    try:
        raw = input("  Nhap so luong tai khoan (1-10): ").strip()
        num = int(raw) if raw else 1
        if num < 1 or num > 10:
            Logger.warning("So luong phai tu 1 den 10!")
            return
    except ValueError:
        Logger.warning("Vui long nhap so nguyen!")
        return

    parallel_reg = ParallelRegistration(num, 1920, 1080)
    results = parallel_reg.register_parallel(AccountStorage, Logger)
    Logger.success(f"Da luu {len(results)} tai khoan vao {INFOACC_DIR}/")


def handle_sequential_registration():
    """Option 3: Dang ky nhieu tai khoan (tuan tu)"""
    try:
        num   = int(input("  So tai khoan: ").strip() or "1")
        delay = int(input("  Cho giua moi lan (giay): ").strip() or "60")
    except ValueError:
        Logger.warning("Vui long nhap so nguyen!")
        return

    for i in range(num):
        service = RegistrationService()
        service.register_one(account_num=i + 1)
        if i < num - 1:
            Logger.info(f"Cho {delay}s truoc tai khoan tiep theo...")
            time.sleep(delay)

    Logger.success(f"Hoan thanh {num} lan dang ky")


def view_csv_accounts():
    """Option 4: Xem tai khoan trong CSV"""
    accounts = AccountStorage.load_accounts_csv()
    W = 62
    print(f"\n{Color.BOLD}{'─' * W}")
    print(f"  DANH SACH TAI KHOAN CSV  ({len(accounts)} tai khoan)")
    print(f"{'─' * W}{Color.RESET}")

    status_styles = {
        "success":              (Color.GREEN, "✓"),
        "pending_verification": (Color.YELLOW, "!"),
    }

    for acc in accounts:
        email    = acc.get("email", "N/A")
        password = acc.get("password", "N/A")
        created  = acc.get("created_at", "N/A")
        print(f"  {Color.GREEN}[✓]{Color.RESET} {email:<35} {Color.GRAY}{created}{Color.RESET}")
        print(f"       {Color.DIM}Pass: {password}{Color.RESET}")

    print(f"{Color.BOLD}{'─' * W}{Color.RESET}\n")


def view_infoacc_accounts():
    """Option 5: Xem tai khoan trong infoacc/"""
    accounts = AccountStorage.load_all_infoacc()
    W = 62
    print(f"\n{Color.BOLD}{'─' * W}")
    print(f"  DANH SACH TAI KHOAN INFOACC/  ({len(accounts)} tai khoan)")
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
    print(f"  {Color.WHITE}1.{Color.RESET}  Dang ky {Color.GREEN}1{Color.RESET} tai khoan")
    print(f"  {Color.WHITE}2.{Color.RESET}  Dang ky {Color.GREEN}song song{Color.RESET} (nhieu browser)")
    print(f"  {Color.WHITE}3.{Color.RESET}  Dang ky {Color.GREEN}tuan tu{Color.RESET} (nhieu tai khoan)")
    print(f"  {Color.WHITE}4.{Color.RESET}  Xem tai khoan {Color.GRAY}(CSV){Color.RESET}")
    print(f"  {Color.WHITE}5.{Color.RESET}  Xem tai khoan {Color.GRAY}(infoacc/){Color.RESET}")
    print(f"  {Color.WHITE}6.{Color.RESET}  {Color.RED}Thoat{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'═' * W}{Color.RESET}")


def main():
    try:
        while True:
            display_menu()
            choice = input(f"  {Color.BOLD}>{Color.RESET} Chon (1-6): ").strip()

            dispatch = {
                "1": handle_single_registration,
                "2": handle_parallel_registration,
                "3": handle_sequential_registration,
                "4": view_csv_accounts,
                "5": view_infoacc_accounts,
            }

            if choice == "6":
                Logger.info("Tam biet!")
                break
            elif choice in dispatch:
                dispatch[choice]()
            else:
                Logger.warning("Lua chon khong hop le, chon tu 1-6!")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n\n  {Color.YELLOW}Dung boi nguoi dung{Color.RESET}\n")
    except Exception as e:
        Logger.error(f"Loi khong xac dinh: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
