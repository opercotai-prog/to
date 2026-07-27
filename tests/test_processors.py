import unittest
from unittest.mock import patch

from ai import processors


class ProcessorsTestCase(unittest.TestCase):
    def test_clean_ai_response_strips_code_fences(self):
        raw = '```json\n{"domain": "AML/ПОД/ФТ", "product": "Card", "actor": "Bank"}\n```'
        self.assertEqual(
            processors.clean_ai_response(raw),
            '{"domain": "AML/ПОД/ФТ", "product": "Card", "actor": "Bank"}',
        )

    def test_classify_law_returns_json_object(self):
        with patch("ai.processors.get_completion", return_value='{"domain": "AML/ПОД/ФТ", "product": "Card", "actor": "Bank"}'):
            result = processors.classify_law("Some law text")
            self.assertEqual(result["domain"], "AML/ПОД/ФТ")
            self.assertEqual(result["product"], "Card")
            self.assertEqual(result["actor"], "Bank")

    def test_summarize_law_returns_plain_text(self):
        with patch("ai.processors.get_completion", return_value="This law changes reporting requirements."):
            self.assertEqual(
                processors.summarize_law("Some law text"),
                "This law changes reporting requirements.",
            )


if __name__ == "__main__":
    unittest.main()
