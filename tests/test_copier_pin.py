"""The Copier version in scoop-bucket-setup must match the one Renovate tracks."""

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class CopierPinTest(unittest.TestCase):
    def test_skill_pin_matches_mise_pin(self):
        tools = tomllib.loads((ROOT / ".config/mise.toml").read_text())["tools"]
        skill = (ROOT / ".ai-rulez/skills/scoop-bucket-setup/SKILL.md").read_text()
        self.assertEqual(re.findall(r"copier@(\S+)", skill), [tools["copier"]])


if __name__ == "__main__":
    unittest.main()
