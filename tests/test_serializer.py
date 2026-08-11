import unittest
import sys
from pathlib import Path

# Đưa src vào sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from xcstrings_tool.core.serializer import dumps, _serialize


class TestSerializer(unittest.TestCase):
    def test_empty_dict(self):
        result = dumps({})
        self.assertEqual(result, "{\n\n}")

    def test_key_value_separator(self):
        data = {"hello": "world"}
        result = dumps(data)
        self.assertIn('"hello" : "world"', result)

    def test_nested_structure(self):
        data = {
            "sourceLanguage": "en",
            "strings": {
                "welcome": {
                    "extractionState": "manual",
                    "localizations": {
                        "vi": {
                            "stringUnit": {
                                "state": "translated",
                                "value": "Chào mừng"
                            }
                        }
                    }
                }
            }
        }
        result = dumps(data)
        self.assertIn('"sourceLanguage" : "en"', result)
        self.assertIn('"welcome" : {', result)
        self.assertIn('"state" : "translated"', result)
        self.assertIn('"value" : "Chào mừng"', result)
        # Không có trailing newline
        self.assertFalse(result.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
