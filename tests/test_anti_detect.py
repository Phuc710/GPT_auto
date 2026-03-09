import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "gpt_auto_reg"
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import anti_detect


class FakeDriver:
    def __init__(self):
        self.cdp_calls = []
        self.urls = []
        self.script_calls = []
        self.cookies_deleted = False

    def execute_cdp_cmd(self, command, params):
        self.cdp_calls.append((command, params))
        return {}

    def get(self, url):
        self.urls.append(url)

    def delete_all_cookies(self):
        self.cookies_deleted = True

    def execute_script(self, script):
        self.script_calls.append(script)
        return None


class AntiDetectTests(unittest.TestCase):
    def test_build_fingerprint_respects_user_agent_platform(self):
        fingerprint = anti_detect.build_fingerprint(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/140.0.7310.61 Safari/537.36"
        )

        self.assertEqual(fingerprint.platform, "Win32")
        self.assertIn(fingerprint.locale, fingerprint.language_header)
        self.assertGreater(fingerprint.screen_width, 0)
        self.assertGreater(fingerprint.screen_height, 0)

    def test_apply_anti_fingerprint_registers_cdp_overrides(self):
        driver = FakeDriver()
        fingerprint = anti_detect.build_fingerprint(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/137.0.7151.41 Safari/537.36"
        )

        anti_detect.apply_anti_fingerprint(driver, fingerprint)

        commands = [command for command, _ in driver.cdp_calls]
        self.assertIn("Network.setUserAgentOverride", commands)
        self.assertIn("Page.addScriptToEvaluateOnNewDocument", commands)

    def test_clear_browser_state_clears_storage_and_cookies(self):
        driver = FakeDriver()

        anti_detect.clear_browser_state(driver)

        commands = [command for command, _ in driver.cdp_calls]
        self.assertIn("Network.enable", commands)
        self.assertIn("Network.clearBrowserCookies", commands)
        self.assertIn("Network.clearBrowserCache", commands)
        self.assertEqual(driver.urls, ["about:blank"])
        self.assertTrue(driver.cookies_deleted)
        self.assertTrue(driver.script_calls)


if __name__ == "__main__":
    unittest.main()
