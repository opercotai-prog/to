import unittest
from pathlib import Path

import pandas as pd
from unittest.mock import patch

from ai.run_analysis import analyze_laws


class RunAnalysisTestCase(unittest.TestCase):
    def test_analyze_laws_adds_ai_columns(self):
        with unittest.mock.patch("pathlib.Path.exists", return_value=True):
            pass

    def test_analyze_laws_adds_ai_columns_with_tmp_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "laws.csv"
            df = pd.DataFrame(
                [
                    {
                        "law_id": "1",
                        "Изменяемый закон и Статья": "Law article",
                        "Точная цитата (Текст нормы / инструкция)": "Some text",
                    }
                ]
            )
            df.to_csv(input_path, index=False)

            with patch("ai.run_analysis.classify_law", return_value={"domain": "AML/ПОД/ФТ", "product": "Card", "actor": "Bank"}), patch(
                "ai.run_analysis.summarize_law", return_value="Short summary"
            ):
                result = analyze_laws(input_path)

            self.assertEqual(result.loc[0, "domain"], "AML/ПОД/ФТ")
            self.assertEqual(result.loc[0, "product"], "Card")
            self.assertEqual(result.loc[0, "actor"], "Bank")
            self.assertEqual(result.loc[0, "business_summary"], "Short summary")
            self.assertTrue({"domain", "product", "actor", "business_summary"}.issubset(result.columns))


if __name__ == "__main__":
    unittest.main()
