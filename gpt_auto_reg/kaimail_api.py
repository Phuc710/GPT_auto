# kaimail_api.py - KaiMail External API Wrapper (HMAC Auth)
# Docs: https://tmail.kaishop.id.vn/api
# Auth: X-API-KEY + X-API-TIMESTAMP + X-API-NONCE + X-API-SIGNATURE (HMAC-SHA256)

import hashlib
import hmac
import json
import os
import re
import sys
import time
import uuid
import requests
from typing import Optional, List, Dict


# ============ EXCEPTION ============
class KaiMailException(Exception):
    """Custom exception for KaiMail API operations"""
    pass


# ============ LOGGER ============
class Logger:
    """Clean logging"""

    @staticmethod
    def info(msg: str):
        print(f"[OK] {msg}")

    @staticmethod
    def success(msg: str):
        print(f"[OK] {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"[!] {msg}", file=sys.stderr)

    @staticmethod
    def error(msg: str):
        print(f"[X] {msg}", file=sys.stderr)

    @staticmethod
    def debug(msg: str):
        print(f"[*] {msg}")

    @staticmethod
    def waiting(msg: str, remaining: int = 0):
        if remaining > 0:
            print(f"[WAIT] {msg} ({remaining}s left)")
        else:
            print(f"[WAIT] {msg}")


# ============ HMAC SIGNER ============
def _build_signature(
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body_raw: bytes,
    secret_key: str,
) -> str:
    """
    Build HMAC-SHA256 signature.
    Base string: METHOD + "\\n" + PATH + "\\n" + TIMESTAMP + "\\n" + NONCE + "\\n" + SHA256(BODY_RAW)
    """
    body_hash = hashlib.sha256(body_raw).hexdigest()
    base_string = "\n".join([method.upper(), path, timestamp, nonce, body_hash])
    sig = hmac.new(
        secret_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return sig


def _hmac_headers(
    method: str,
    path: str,
    body_raw: bytes,
    api_key: str,
    secret_key: str,
) -> Dict[str, str]:
    """Return the four HMAC auth headers for a request."""
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex  # unique per request
    signature = _build_signature(method, path, timestamp, nonce, body_raw, secret_key)
    return {
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
        "X-API-TIMESTAMP": timestamp,
        "X-API-NONCE": nonce,
        "X-API-SIGNATURE": signature,
    }


# ============ KAIMAIL API ============
class KaiMailAPI:
    """
    KaiMail External API wrapper (HMAC-SHA256 auth).
    Endpoint base: https://tmail.kaishop.id.vn/api
    """

    DOMAIN = "kaishop.id.vn"
    NAME_TYPE = "en"

    def __init__(
        self,
        base_url: str = "https://tmail.kaishop.id.vn",
        api_key: str = None,
        secret_key: str = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.email: Optional[str] = None
        self.email_id: Optional[int] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[dict] = None,
        params: Optional[dict] = None,
        timeout: int = 15,
    ) -> Optional[requests.Response]:
        """Make a signed HMAC request."""
        url = f"{self.base_url}{path}"
        body_raw = json.dumps(body, separators=(",", ":")).encode("utf-8") if body else b""
        headers = _hmac_headers(method, path, body_raw, self.api_key, self.secret_key)

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                data=body_raw if body else None,
                params=params,
                timeout=timeout,
            )
            return response
        except requests.RequestException as e:
            Logger.error(f"Lỗi kết nối API: {e}")
            return False

    # ------------------------------------------------------------------
    # Email management
    # ------------------------------------------------------------------

    def create_email(self, quantity: int = 1) -> Optional[str]:
        """
        Create one mailbox on kaishop.id.vn (English name).
        Returns the email address on success, None on failure.
        """
        payload = {
            "domain": self.DOMAIN,
            "name_type": self.NAME_TYPE,
            "quantity": 1,  # always 1 per registration
        }

        Logger.info("Đang tạo email tạm thời qua HMAC API...")

        resp = self._request("POST", "/api/emails.php", body=payload)

        if resp is None:
            Logger.error("No response from server")
            return None

        if resp.status_code == 429:
            Logger.error("Rate limited (429) — wait a moment and retry")
            return None

        try:
            data = resp.json()
        except ValueError:
            Logger.error(f"Invalid JSON (HTTP {resp.status_code}): {resp.text[:200]}")
            return None

        if resp.status_code in (200, 201) and data.get("success"):
            emails = data.get("emails") or data.get("data") or []
            if emails:
                first = emails[0]
                self.email = first.get("email") or first.get("address")
                self.email_id = first.get("id")
                Logger.success(f"Email created: {self.email}")
                return self.email
            # Some APIs return a single-object response
            if data.get("email"):
                self.email = data["email"]
                self.email_id = data.get("id")
                Logger.success(f"Email created: {self.email}")
                return self.email

        Logger.error(
            f"Email creation failed (HTTP {resp.status_code}): "
            f"{data.get('message') or data.get('error') or resp.text[:200]}"
        )
        return None

    def check_email_exists(self, email: str) -> bool:
        """Check if a mailbox exists (GET /api/emails.php?email=...)."""
        resp = self._request("GET", "/api/emails.php", params={"email": email})
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return bool(data.get("exists") or data.get("success"))
            except ValueError:
                pass
        return False

    def delete_email(self, email: str) -> bool:
        """Delete a mailbox."""
        resp = self._request("DELETE", "/api/emails.php", body={"email": email})
        if resp and resp.status_code in (200, 204):
            return True
        return False

    # ------------------------------------------------------------------
    # Message management
    # ------------------------------------------------------------------

    def get_messages(self, email: Optional[str] = None, limit: int = 30) -> List[Dict]:
        """List messages for the current (or given) email address."""
        target = email or self.email
        if not target:
            Logger.warning("No email set — cannot fetch messages")
            return []

        resp = self._request(
            "GET",
            "/api/messages.php",
            params={"email": target, "limit": limit},
        )

        if resp is None:
            return []

        if resp.status_code == 200:
            try:
                data = resp.json()
                return data.get("messages") or data.get("data") or []
            except ValueError:
                pass

        return []

    def get_message_detail(self, message_id: int) -> Optional[Dict]:
        """Get full message content by ID."""
        resp = self._request("GET", "/api/messages.php", params={"id": message_id})
        if resp and resp.status_code == 200:
            try:
                return resp.json()
            except ValueError:
                pass
        return None

    def delete_messages(self, email: str, ids: Optional[List[int]] = None, delete_all: bool = False) -> bool:
        """Delete selected messages or all messages in a mailbox."""
        body: Dict = {"email": email}
        if delete_all:
            body["delete_all"] = True
        elif ids:
            body["ids"] = ids
        else:
            return False

        resp = self._request("DELETE", "/api/messages.php", body=body)
        return bool(resp and resp.status_code in (200, 204))

    # ------------------------------------------------------------------
    # Verification code helper
    # ------------------------------------------------------------------

    def wait_for_openai_email(self, timeout: int = 300, interval: int = 5) -> Optional[str]:
        """Kiểm tra hộp thư cho đến khi email xác minh OpenAI đến."""
        Logger.waiting("Đang chờ email xác minh OpenAI...")

        if not self.email:
            Logger.error("No email set")
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            remaining = int(timeout - (time.time() - start_time))
            messages = self.get_messages()

            for msg in messages:
                sender = (msg.get("from_email") or "").lower()
                sender_name = (msg.get("from_name") or "").lower()
                subject = msg.get("subject") or ""

                if (
                    "openai" in sender
                    or "openai" in sender_name
                    or "chatgpt" in subject.lower()
                ):
                    Logger.success(f"Found email from: {msg.get('from_name', sender)}")

                    # Try subject first, then body
                    code = self._extract_code(subject)
                    if not code:
                        # Fetch full message for body content
                        msg_id = msg.get("id")
                        if msg_id:
                            detail = self.get_message_detail(msg_id)
                            if detail:
                                body_text = (detail.get("body_text") or "") + " " + (detail.get("body_html") or "")
                                code = self._extract_code(body_text)

                    if code:
                        Logger.success(f"Verification code: {code}")
                        return code

            Logger.debug(f"Đang kiểm tra hộp thư... (còn {remaining}s)")
            time.sleep(interval)

        Logger.error("Hết thời gian chờ email xác minh")
        return None

    @staticmethod
    def _extract_code(text: str) -> Optional[str]:
        """Extract 6-digit verification code from text."""
        if not text:
            return None
        patterns = [
            r"\b(\d{6})\b",
            r"code[:\s]+(\d{6})",
            r"verification[:\s]+(\d{6})",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        return None


# ============ QUICK TEST ============
if __name__ == "__main__":
    from config import KAIMAIL_BASE_URL, KAIMAIL_API_KEY, KAIMAIL_SECRET_KEY

    print("Test KaiMail HMAC API...\n")
    km = KaiMailAPI(base_url=KAIMAIL_BASE_URL, api_key=KAIMAIL_API_KEY, secret_key=KAIMAIL_SECRET_KEY)
    email = km.create_email()
    if email:
        print(f"\nOK Email created: {email}")
    else:
        print("\nX Email creation failed")
