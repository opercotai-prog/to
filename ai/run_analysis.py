from pathlib import Path

import pandas as pd

from ai.processors import classify_law, summarize_law


def analyze_laws(input_path, output_path=None):
    """Process a CSV file of laws and enrich it with AI-generated classification and summary columns."""
    input_path = Path(input_path)
    if output_path is None:
        output_path = input_path.with_name(f"{input_path.stem}_processed.csv")
    else:
        output_path = Path(output_path)

    df = pd.read_csv(input_path)

    if df.empty:
        return df

    results = []
    for _, row in df.iterrows():
        law_text = "\n".join(
            [
                str(row.get("Изменяемый закон и Статья", "")),
                str(row.get("Точная цитата (Текст нормы / инструкция)", "")),
            ]
        ).strip()

        classification = classify_law(law_text)
        summary = summarize_law(law_text)

        results.append(
            {
                "domain": classification.get("domain", "Общее"),
                "product": classification.get("product", "Unknown"),
                "actor": classification.get("actor", "Bank"),
                "business_summary": summary,
            }
        )

    enriched = df.copy()
    enriched["domain"] = [item["domain"] for item in results]
    enriched["product"] = [item["product"] for item in results]
    enriched["actor"] = [item["actor"] for item in results]
    enriched["business_summary"] = [item["business_summary"] for item in results]

    enriched.to_csv(output_path, index=False)
    return enriched


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run law analysis over a CSV file")
    parser.add_argument("input_csv", nargs="?", default="data/laws/data.csv")
    parser.add_argument("output_csv", nargs="?", default=None)
    args = parser.parse_args()

    analyze_laws(args.input_csv, args.output_csv)
    print(f"Processed data saved to {args.output_csv or 'default output path'}")
