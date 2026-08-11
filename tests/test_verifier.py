import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcstrings_tool.services.verifier import check_translations, check_format_preserved


class TestVerifier(unittest.TestCase):
    def test_placeholder_mismatch(self):
        data = {
            "sourceLanguage": "en",
            "strings": {
                "user_score": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "User %@ scored %d points"}},
                        "vi": {"stringUnit": {"state": "translated", "value": "Người dùng %@ ghi được điểm"}}  # thiếu %d
                    }
                }
            }
        }
        warnings, stats = check_translations(data, "vi")
        self.assertEqual(stats["placeholder_mismatch"], 1)
        self.assertTrue(any("placeholder lệch" in w for w in warnings))

    def test_placeholder_match(self):
        data = {
            "sourceLanguage": "en",
            "strings": {
                "user_score": {
                    "localizations": {
                        "en": {"stringUnit": {"state": "translated", "value": "User %@ scored %d points"}},
                        "vi": {"stringUnit": {"state": "translated", "value": "Người dùng %@ đạt %d điểm"}}
                    }
                }
            }
        }
        warnings, stats = check_translations(data, "vi")
        self.assertEqual(stats["placeholder_mismatch"], 0)


if __name__ == "__main__":
    unittest.main()
