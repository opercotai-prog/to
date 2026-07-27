import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ai.ai_client import get_completion


class AiClientTestCase(unittest.TestCase):
    def test_get_completion_retries_next_model_on_error(self):
        class FakeCompletions:
            def __init__(self):
                self.calls = 0

            def create(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise Exception("404 model unavailable")
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))]
                )

        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

        with patch("ai.ai_client.os.getenv", return_value="test-key"), patch(
            "ai.ai_client.OpenAI", return_value=fake_client
        ), patch("builtins.print") as mocked_print:
            result = get_completion("hello")

        self.assertEqual(result, "ok")
        self.assertEqual(fake_client.chat.completions.calls, 2)
        self.assertTrue(any("Пробую модель" in str(call.args[0]) for call in mocked_print.call_args_list))


if __name__ == "__main__":
    unittest.main()
