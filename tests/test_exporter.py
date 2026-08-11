import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcstrings_tool.services.exporter import export_all_rows, export_untranslated_rows


class TestExporter(unittest.TestCase):
    def setUp(self):
        self.sample_data = {
            "sourceLanguage": "en",
            "strings": {
                "greeting": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "Hello"}},
                        "vi": {"stringUnit": {"state": "translated", "value": "Xin chào"}},
                    }
                },
                "bye": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "Goodbye"}},
                        "vi": {"stringUnit": {"state": "needs_review", "value": "Tạm biệt"}},
                    }
                },
                "new_key": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "New Item"}}
                    }
                }
            }
        }

    def test_export_all_long(self):
        rows, fields = export_all_rows(self.sample_data, ["vi"], mode="long")
        self.assertEqual(len(rows), 3)
        self.assertEqual(fields, ["key", "variant", "source_value", "target_value"])

    def test_export_untranslated_long(self):
        rows, _ = export_untranslated_rows(self.sample_data, ["vi"], mode="long")
        # 'bye' (needs_review) và 'new_key' (thiếu vi) là chưa dịch
        self.assertEqual(len(rows), 2)
        keys = {r["key"] for r in rows}
        self.assertIn("bye", keys)
        self.assertIn("new_key", keys)

    def test_export_wide(self):
        rows, fields = export_all_rows(self.sample_data, ["vi", "ja"], mode="wide")
        self.assertEqual(len(rows), 3)
        self.assertIn("vi_target", fields)
        self.assertIn("ja_target", fields)


if __name__ == "__main__":
    unittest.main()
