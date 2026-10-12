"""
Unit tests for Cloud Updates Engine
"""
import unittest
import os
import json
import tempfile

from core.cloud_updater import (
    is_newer_version,
    parse_version_tuple,
    get_cloud_config,
    save_cloud_config,
    find_local_installer,
    generate_cloud_manifest_file,
    check_for_updates
)


class TestCloudUpdater(unittest.TestCase):
    def test_version_parsing_and_comparison(self):
        self.assertEqual(parse_version_tuple("2.3.0"), (2, 3, 0))
        self.assertEqual(parse_version_tuple("v2.3.1"), (2, 3, 1))
        self.assertEqual(parse_version_tuple("3.0"), (3, 0, 0))

        self.assertTrue(is_newer_version("2.3.1", "2.3.0"))
        self.assertTrue(is_newer_version("v2.4.0", "2.3.0"))
        self.assertTrue(is_newer_version("3.0.0", "2.3.0"))

        self.assertFalse(is_newer_version("2.3.0", "2.3.0"))
        self.assertFalse(is_newer_version("2.2.9", "2.3.0"))
        self.assertFalse(is_newer_version("1.9.9", "2.3.0"))

    def test_cloud_config_persistence(self):
        cfg = get_cloud_config()
        self.assertIn("manifest_url", cfg)

        orig_url = cfg.get("manifest_url")
        test_url = "https://example.com/test_version.json"
        save_cloud_config({"enabled": True, "manifest_url": test_url})

        updated = get_cloud_config()
        self.assertEqual(updated["manifest_url"], test_url)

        # Restore
        save_cloud_config({"enabled": True, "manifest_url": orig_url})

    def test_local_installer_detection(self):
        installer = find_local_installer()
        self.assertIsNotNone(installer)
        self.assertTrue(os.path.exists(installer))
        self.assertTrue(installer.endswith("Silver Premium Invoice Generator Setup.exe"))

    def test_generate_cloud_manifest(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            out = generate_cloud_manifest_file(temp_path)
            self.assertTrue(os.path.exists(out))
            with open(out, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("version", data)
            self.assertIn("installer_url", data)
            self.assertIn("changelog", data)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_offline_fallback(self):
        # Invalid host should not crash; must return structured response
        res = check_for_updates("http://invalid.domain.that.does.not.exist.test/version.json")
        self.assertIsInstance(res, dict)
        self.assertIn("current_version", res)
        self.assertIn("message", res)


if __name__ == "__main__":
    unittest.main()
