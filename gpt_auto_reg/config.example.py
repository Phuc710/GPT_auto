# config.example.py - Copy to config.py and fill in your local values

# Proxy settings (None or "http://user:pass@ip:port")
PROXY = None

# Browser settings
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# Timing (seconds)
WAIT_TIME = 20
MAX_RETRY = 3
CHECK_EMAIL_INTERVAL = 5
EMAIL_TIMEOUT = 300

# Default password
DEFAULT_PASSWORD = "change-me"

# Output files
ACCOUNTS_FILE = "accounts.json"
ACCOUNTS_CSV = "accounts.csv"

# KaiMail External API
KAIMAIL_BASE_URL = "https://tmail.kaishop.id.vn"
KAIMAIL_API_KEY = "your-api-key"
KAIMAIL_SECRET_KEY = "your-secret-key"
KAIMAIL_DOMAIN = "kaishop.id.vn"
KAIMAIL_NAME_TYPE = "en"

# Anti-Detection
USE_ANTI_DETECT = True
RANDOM_DELAYS = True
MIN_DELAY_MS = 500
MAX_DELAY_MS = 2000
