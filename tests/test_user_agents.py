import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "gpt_auto_reg"
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

from user_agents import DEFAULT_USER_AGENT_CATALOG


class UserAgentCatalogTests(unittest.TestCase):
    def test_all_returns_copy(self):
        entries = DEFAULT_USER_AGENT_CATALOG.all()

        self.assertEqual(len(entries), len(DEFAULT_USER_AGENT_CATALOG.entries))
        self.assertIsInstance(entries, list)
        self.assertIsNot(entries, DEFAULT_USER_AGENT_CATALOG.entries)

    def test_chromium_only_pool_contains_only_chromium_agents(self):
        chromium_entries = DEFAULT_USER_AGENT_CATALOG.chromium()

        self.assertTrue(chromium_entries)
        self.assertTrue(
            all("Chrome/" in entry or "Edg/" in entry for entry in chromium_entries)
        )

    def test_pick_random_chromium_only_returns_compatible_agent(self):
        for _ in range(20):
            user_agent = DEFAULT_USER_AGENT_CATALOG.pick_random(chromium_only=True)
            self.assertTrue("Chrome/" in user_agent or "Edg/" in user_agent)


if __name__ == "__main__":
    unittest.main()
