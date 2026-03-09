# anti_detect.py - Anti-Detection Module for GPT Auto Registration
"""
Anti-detection features for browser automation
Includes User-Agent rotation, fingerprint generation, and timing randomization
"""

import random
import hashlib
import time
import uuid
import sys


# ============ LOGGER ============
class Logger:
    """Clean logging for anti-detect module"""
    
    @staticmethod
    def info(msg: str):
        print(f"[✓] {msg}")
    
    @staticmethod
    def debug(msg: str):
        print(f"[•] {msg}")


# ============ USER AGENTS ============
# Real browser User-Agents (updated Jan 2026)
USER_AGENTS = [
    # --- Desktop Windows ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    
    # --- Desktop Mac ---
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    
    # --- Desktop Linux ---
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",

    # --- Mobile Android ---
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36",
    
    # --- Mobile iOS ---
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",

    # --- Tablet ---
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-X900) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

# ============ SCREEN RESOLUTIONS ============
RESOLUTIONS = [
    "1920x1080", "1366x768", "1536x864", "1440x900", "1280x720",
    "2560x1440", "1600x900", "1680x1050", "1280x800"
]

# ============ TIMEZONES ============
TIMEZONES = [-8, -7, -6, -5, -4, 0, 1, 7, 8]

# ============ LANGUAGES ============
LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-GB,en;q=0.9",
    "en-CA,en;q=0.9",
]


# ============ FUNCTIONS ============
def get_random_user_agent() -> str:
    """Get a random User-Agent string"""
    return random.choice(USER_AGENTS)


def get_fingerprint() -> str:
    """Generate realistic browser fingerprint hash"""
    components = [
        str(int(time.time() * 1000)),
        str(random.random()),
        random.choice(RESOLUTIONS),
        str(random.choice(TIMEZONES)),
        random.choice(LANGUAGES).split(",")[0],
        random.choice(["Win32", "MacIntel", "Linux x86_64"]),
        str(random.randint(2, 16)),
        str(random.randint(4, 32)),
        str(uuid.uuid4()),
    ]
    return hashlib.md5("|".join(components).encode()).hexdigest()


def get_canvas_fingerprint() -> str:
    """Generate a realistic canvas fingerprint hash"""
    seed = str(time.time()) + str(random.random())
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def random_delay(min_ms: int = 300, max_ms: int = 1200):
    """
    Random delay to mimic human behavior
    """
    delay = random.randint(min_ms, max_ms) / 1000
    delay += random.uniform(0, 0.15)
    time.sleep(delay)


def random_typing_delay():
    """Simulate human typing speed between keystrokes"""
    delay = random.uniform(0.05, 0.25)
    time.sleep(delay)


def get_full_fingerprint() -> dict:
    """Generate complete browser fingerprint for anti-detection"""
    screen = random.choice(RESOLUTIONS)
    width, height = screen.split("x")
    
    return {
        "hash": get_fingerprint(),
        "canvas": get_canvas_fingerprint(),
        "screen": {
            "width": int(width),
            "height": int(height),
            "colorDepth": random.choice([24, 32]),
            "pixelRatio": random.choice([1, 1.5, 2]),
        },
        "timezone": random.choice(TIMEZONES),
        "language": random.choice(LANGUAGES).split(",")[0],
        "platform": random.choice(["Win32", "MacIntel", "Linux x86_64"]),
        "cpuCores": random.randint(2, 16),
        "memory": random.randint(4, 32),
        "sessionId": str(uuid.uuid4()),
    }


def add_random_mouse_movements(driver):
    """
    Add random mouse movements to appear more human-like
    """
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        
        actions = ActionChains(driver)
        for _ in range(random.randint(1, 3)):
            x_offset = random.randint(-100, 100)
            y_offset = random.randint(-100, 100)
            actions.move_by_offset(x_offset, y_offset)
            time.sleep(random.uniform(0.1, 0.3))
        actions.perform()
    except Exception:
        pass


def random_scroll(driver):
    """Execute random scroll to simulate user behavior"""
    try:
        scroll_amount = random.randint(100, 500)
        direction = random.choice([1, -1])
        driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction})")
        random_delay(200, 600)
    except Exception:
        pass


# ============ TEST ============
if __name__ == "__main__":
    print("Test Anti-Detection Module\n")
    
    ua = get_random_user_agent()
    print(f"User-Agent ngẫu nhiên: {ua[:70]}...")
    
    fp = get_fingerprint()
    print(f"Fingerprint: {fp}")
    
    canvas = get_canvas_fingerprint()
    print(f"Canvas Fingerprint: {canvas}")
    
    full_fp = get_full_fingerprint()
    print(f"\nFingerprint đầy đủ:")
    print(f"  Screen: {full_fp['screen']['width']}x{full_fp['screen']['height']}")
    print(f"  Platform: {full_fp['platform']}")
    print(f"  CPU Cores: {full_fp['cpuCores']}")
    print(f"  Memory: {full_fp['memory']}GB")
