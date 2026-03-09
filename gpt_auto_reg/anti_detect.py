# anti_detect.py - Anti-detection helpers for GPT auto registration

from __future__ import annotations

import hashlib
import random
import time
import uuid
from dataclasses import dataclass

from user_agents import DEFAULT_USER_AGENT_CATALOG


RESOLUTIONS = [
    (1920, 1080),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1600, 900),
    (1680, 1050),
]

TIMEZONES = [
    "America/Los_Angeles",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
    "Europe/London",
    "Europe/Berlin",
    "Asia/Bangkok",
    "Asia/Singapore",
]

LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,vi;q=0.8",
]

WEBGL_PROFILES = [
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 6600 Direct3D11 vs_5_0 ps_5_0)"),
]


def _platform_from_user_agent(user_agent: str) -> str:
    if "Windows" in user_agent:
        return "Win32"
    if "Macintosh" in user_agent:
        return "MacIntel"
    return "Linux x86_64"


@dataclass(frozen=True, slots=True)
class BrowserFingerprint:
    user_agent: str
    language_header: str
    locale: str
    timezone: str
    platform: str
    screen_width: int
    screen_height: int
    color_depth: int
    pixel_ratio: float
    hardware_concurrency: int
    device_memory: int
    webgl_vendor: str
    webgl_renderer: str
    canvas_seed: str
    session_id: str

    @property
    def window_size_argument(self) -> str:
        return f"{self.screen_width},{self.screen_height}"


def get_random_user_agent() -> str:
    """Pick a Chromium-compatible desktop User-Agent."""
    return DEFAULT_USER_AGENT_CATALOG.pick_random(chromium_only=True)


def build_fingerprint(user_agent: str | None = None) -> BrowserFingerprint:
    """Build a consistent random fingerprint for a single browser session."""
    ua = user_agent or get_random_user_agent()
    screen_width, screen_height = random.choice(RESOLUTIONS)
    language_header = random.choice(LANGUAGES)
    locale = language_header.split(",")[0]
    webgl_vendor, webgl_renderer = random.choice(WEBGL_PROFILES)

    return BrowserFingerprint(
        user_agent=ua,
        language_header=language_header,
        locale=locale,
        timezone=random.choice(TIMEZONES),
        platform=_platform_from_user_agent(ua),
        screen_width=screen_width,
        screen_height=screen_height,
        color_depth=random.choice([24, 30, 32]),
        pixel_ratio=random.choice([1, 1.25, 1.5]),
        hardware_concurrency=random.choice([4, 6, 8, 12]),
        device_memory=random.choice([4, 8, 16]),
        webgl_vendor=webgl_vendor,
        webgl_renderer=webgl_renderer,
        canvas_seed=hashlib.sha256(f"{time.time()}:{uuid.uuid4()}".encode()).hexdigest()[:16],
        session_id=str(uuid.uuid4()),
    )


def apply_anti_fingerprint(driver, fingerprint: BrowserFingerprint) -> None:
    """Apply CDP overrides and JS patches before navigating to the target site."""
    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride",
        {
            "userAgent": fingerprint.user_agent,
            "acceptLanguage": fingerprint.language_header,
            "platform": fingerprint.platform,
        },
    )

    try:
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": fingerprint.timezone})
    except Exception:
        pass

    try:
        driver.execute_cdp_cmd("Emulation.setLocaleOverride", {"locale": fingerprint.locale})
    except Exception:
        pass

    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": _build_stealth_script(fingerprint)},
    )


def clear_browser_state(driver) -> None:
    """Best-effort cleanup for cookies, cache, and origin storage in a fresh session."""
    try:
        driver.execute_cdp_cmd("Network.enable", {})
        driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
        driver.execute_cdp_cmd("Network.clearBrowserCache", {})
    except Exception:
        pass

    try:
        driver.get("about:blank")
        driver.delete_all_cookies()
        driver.execute_script(
            """
            try { window.localStorage.clear(); } catch (e) {}
            try { window.sessionStorage.clear(); } catch (e) {}
            try {
                if (window.indexedDB && indexedDB.databases) {
                    indexedDB.databases().then((dbs) => {
                        for (const db of dbs) {
                            if (db && db.name) {
                                indexedDB.deleteDatabase(db.name);
                            }
                        }
                    });
                }
            } catch (e) {}
            """
        )
    except Exception:
        pass


def get_fingerprint() -> str:
    """Generate a short fingerprint hash for logging or tracing."""
    fingerprint = build_fingerprint()
    raw = (
        f"{fingerprint.user_agent}|{fingerprint.platform}|{fingerprint.screen_width}x"
        f"{fingerprint.screen_height}|{fingerprint.timezone}|{fingerprint.session_id}"
    )
    return hashlib.md5(raw.encode()).hexdigest()


def get_canvas_fingerprint() -> str:
    """Generate a random canvas fingerprint token."""
    return hashlib.sha256(f"{time.time()}:{random.random()}".encode()).hexdigest()[:32]


def get_full_fingerprint() -> dict:
    """Compatibility wrapper returning the fingerprint as a plain dict."""
    fingerprint = build_fingerprint()
    return {
        "hash": fingerprint.session_id,
        "canvas": fingerprint.canvas_seed,
        "screen": {
            "width": fingerprint.screen_width,
            "height": fingerprint.screen_height,
            "colorDepth": fingerprint.color_depth,
            "pixelRatio": fingerprint.pixel_ratio,
        },
        "timezone": fingerprint.timezone,
        "language": fingerprint.locale,
        "platform": fingerprint.platform,
        "cpuCores": fingerprint.hardware_concurrency,
        "memory": fingerprint.device_memory,
        "sessionId": fingerprint.session_id,
        "userAgent": fingerprint.user_agent,
    }


def random_delay(min_ms: int = 300, max_ms: int = 1200) -> None:
    delay = random.randint(min_ms, max_ms) / 1000
    delay += random.uniform(0, 0.15)
    time.sleep(delay)


def random_typing_delay() -> None:
    time.sleep(random.uniform(0.05, 0.25))


def add_random_mouse_movements(driver) -> None:
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


def random_scroll(driver) -> None:
    try:
        scroll_amount = random.randint(100, 500)
        direction = random.choice([1, -1])
        driver.execute_script(f"window.scrollBy(0, {scroll_amount * direction})")
        random_delay(200, 600)
    except Exception:
        pass


def _build_stealth_script(fingerprint: BrowserFingerprint) -> str:
    return f"""
const override = (obj, key, value) => {{
  Object.defineProperty(obj, key, {{
    get: () => value,
    configurable: true,
  }});
}};

override(Navigator.prototype, 'webdriver', undefined);
override(Navigator.prototype, 'platform', '{fingerprint.platform}');
override(Navigator.prototype, 'language', '{fingerprint.locale}');
override(Navigator.prototype, 'languages', ['{fingerprint.locale}', 'en']);
override(Navigator.prototype, 'hardwareConcurrency', {fingerprint.hardware_concurrency});
override(Navigator.prototype, 'deviceMemory', {fingerprint.device_memory});
override(Navigator.prototype, 'vendor', 'Google Inc.');
override(Screen.prototype, 'width', {fingerprint.screen_width});
override(Screen.prototype, 'height', {fingerprint.screen_height});
override(Screen.prototype, 'colorDepth', {fingerprint.color_depth});
override(window, 'devicePixelRatio', {fingerprint.pixel_ratio});

window.chrome = window.chrome || {{ runtime: {{}} }};

const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {{
  window.navigator.permissions.query = (parameters) => (
    parameters && parameters.name === 'notifications'
      ? Promise.resolve({{ state: Notification.permission }})
      : originalQuery(parameters)
  );
}}

override(Navigator.prototype, 'plugins', [
  {{ name: 'Chrome PDF Plugin' }},
  {{ name: 'Chrome PDF Viewer' }},
  {{ name: 'Native Client' }},
]);

const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {{
  if (parameter === 37445) return '{fingerprint.webgl_vendor}';
  if (parameter === 37446) return '{fingerprint.webgl_renderer}';
  return getParameter.call(this, parameter);
}};

const canvasSeed = '{fingerprint.canvas_seed}';
const toDataURL = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(...args) {{
  try {{
    const context = this.getContext('2d');
    if (context) {{
      context.save();
      const noise = parseInt(canvasSeed.slice(0, 2), 16) % 5;
      context.fillStyle = `rgba(${{noise}}, 0, 0, 0.01)`;
      context.fillRect(0, 0, 1, 1);
      context.restore();
    }}
  }} catch (e) {{}}
  return toDataURL.apply(this, args);
}};
"""
