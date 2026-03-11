# config.py - Cấu hình tự động load từ .env (portable, không hardcode)

import os
from pathlib import Path

# Load .env nếu có (không bắt buộc - fallback về biến môi trường)
try:
    from dotenv import load_dotenv
    _env_file = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_file)
except ImportError:
    pass  # dotenv không bắt buộc


# ──────────────────────────────────────────
# KaiMail External API (HMAC Auth)
# Docs: https://tmail.kaishop.id.vn/api
# ──────────────────────────────────────────
KAIMAIL_BASE_URL  = os.getenv("KAIMAIL_BASE_URL",  "https://tmail.kaishop.id.vn")
KAIMAIL_API_KEY   = os.getenv("KAIMAIL_API_KEY",   "")
KAIMAIL_SECRET_KEY= os.getenv("KAIMAIL_SECRET_KEY","")
KAIMAIL_DOMAIN    = os.getenv("KAIMAIL_DOMAIN",    "kaishop.id.vn")
KAIMAIL_NAME_TYPE = os.getenv("KAIMAIL_NAME_TYPE", "en")

# ──────────────────────────────────────────
# Registration settings
# ──────────────────────────────────────────
DEFAULT_PASSWORD   = os.getenv("DEFAULT_PASSWORD", "kaishop@12345")
WAIT_TIME          = int(os.getenv("WAIT_TIME",          "20"))
MAX_RETRY          = int(os.getenv("MAX_RETRY",           "3"))
CHECK_EMAIL_INTERVAL = int(os.getenv("CHECK_EMAIL_INTERVAL", "5"))
EMAIL_TIMEOUT        = int(os.getenv("EMAIL_TIMEOUT",       "300"))

# ──────────────────────────────────────────
# Output files
# ──────────────────────────────────────────
ACCOUNTS_FILE = os.getenv("ACCOUNTS_FILE", "accounts.json")
ACCOUNTS_CSV  = os.getenv("ACCOUNTS_CSV",  "accounts.csv")

# ──────────────────────────────────────────
# Anti-Detection (tùy chọn, không ảnh hưởng logic)
# ──────────────────────────────────────────
USE_ANTI_DETECT  = True
RANDOM_DELAYS    = True
MIN_DELAY_MS     = 500
MAX_DELAY_MS     = 2000
