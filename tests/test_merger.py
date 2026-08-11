import copy
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcstrings_tool.services.merger import merge_long, merge_wide


class TestMerger(unittest.TestCase):
    def setUp(self):
        self.sample_data = {
            "sourceLanguage": "en",
            "strings": {
                "welcome": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "Welcome"}}
                    }
                },
                "items_count": {
                    "localizations": {
                        "en": {
                            "variations": {
                                "plural": {
                                    "one": {"stringUnit": {"state": "translated", "value": "%d item"}},
                                    "other": {"stringUnit": {"state": "translated", "value": "%d items"}}
                                }
                            }
                        }
                    }
                }
            }
        }

    def test_merge_long_simple(self):
        data = copy.deepcopy(self.sample_data)
        rows = [
            {"key": "welcome", "variant": "", "target_value": "Chào mừng"},
        ]
        report = merge_long(data, rows, target_lang="vi")
        self.assertEqual(report["merged_count"]["vi"], 1)

        vi_loc = data["strings"]["welcome"]["localizations"]["vi"]
        self.assertEqual(vi_loc["stringUnit"]["value"], "Chào mừng")
        self.assertEqual(vi_loc["stringUnit"]["state"], "translated")

    def test_merge_long_plural(self):
        data = copy.deepcopy(self.sample_data)
        rows = [
            {"key": "items_count", "variant": "plural.one", "target_value": "%d món đồ"},
            {"key": "items_count", "variant": "plural.other", "target_value": "%d món đồ"},
        ]
        report = merge_long(data, rows, target_lang="vi")
        self.assertEqual(report["merged_count"]["vi"], 2)

        vi_var = data["strings"]["items_count"]["localizations"]["vi"]["variations"]["plural"]
        self.assertEqual(vi_var["one"]["stringUnit"]["value"], "%d món đồ")
        self.assertEqual(vi_var["other"]["stringUnit"]["value"], "%d món đồ")

    def test_merge_wide(self):
        data = copy.deepcopy(self.sample_data)
        rows = [
            {"key": "welcome", "variant": "", "vi_target": "Chào mừng", "ja_target": "ようこそ"},
        ]
        fieldnames = ["key", "variant", "source_value", "vi_target", "ja_target"]
        report = merge_wide(data, rows, fieldnames)
        self.assertEqual(report["merged_count"]["vi"], 1)
        self.assertEqual(report["merged_count"]["ja"], 1)

        self.assertEqual(data["strings"]["welcome"]["localizations"]["ja"]["stringUnit"]["value"], "ようこそ")


if __name__ == "__main__":
    unittest.main()
