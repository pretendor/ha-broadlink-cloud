"""Check the packaged custom integration manifest without Home Assistant installed."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "broadlink_cloud"


class ManifestTests(unittest.TestCase):
    def test_manifest_and_config_flow_are_present(self):
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["domain"], "broadlink_cloud")
        self.assertTrue(manifest["config_flow"])
        self.assertTrue((INTEGRATION / "config_flow.py").is_file())
        self.assertTrue((INTEGRATION / "auth.py").is_file())

    def test_core_cryptography_is_not_pinned_by_custom_integration(self):
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        requirements = manifest["requirements"]
        self.assertIn("httpx==0.28.1", requirements)
        self.assertFalse(
            any(item.lower().startswith("cryptography") for item in requirements),
            "Cryptography ships with Home Assistant Core: don't pin an older release.",
        )

    def test_marketplace_package_metadata(self):
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.1.2")
        self.assertTrue(hacs["name"])
        self.assertIn("issues", manifest["issue_tracker"])
        self.assertEqual(manifest["categories"], ["buttons_remotes"])
        self.assertTrue((INTEGRATION / "brand" / "icon.png").is_file())


if __name__ == "__main__":
    unittest.main()
