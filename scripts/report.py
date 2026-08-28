#!/usr/bin/env python3
import yaml
from pathlib import Path
from datetime import datetime

DATA_DIR = Path.home() / "kiarsy" / "data"
OUT_DIR = Path.home() / "kiarsy" / "output"

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def pretty(text):
    # Capitalize only the first letter; keeps IDPs and apostrophes correct
    return text[0].upper() + text[1:]

def main():
    symbols = []
    for file in (DATA_DIR / "cultures").rglob("*.yaml"):
        data = load_yaml(file)
        if data: symbols.append(data)

    company_data = load_yaml(DATA_DIR / "companies" / "flat6labs.yaml")
    test_data = load_yaml(DATA_DIR / "tests" / "flat6labs_test.yaml")

    merged_values = {}
    for val, weight in company_data.get('channel_1', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight
    for val, weight in test_data.get('channel_2', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight

    top_values = sorted(merged_values.items(), key=lambda x: x[1], reverse=True)

    symbol_scores = []
    for sym in symbols:
        score = 0
        matched = []
        for v in sym.get('values', []):
            if v in merged_values:
                score += merged_values[v]
                matched.append(v)
        symbol_scores.append((score, sym, matched))

    symbol_scores.sort(reverse=True, key=lambda x: x[0])

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = OUT_DIR / f"{company_data['id']}_recommendation.md"

    with open(report_path, 'w') as f:
        f.write(f"# KIARSY Design Recommendation: {company_data['name']}\n")
        f.write(f"*Generated on {today}*\n\n")

        f.write("## 1. Company Value Profile (Merged Data)\n")
        f.write("Based on web profiling (Channel 1) and B2B client test (Channel 2):\n\n")
        for val, score in top_values[:5]:
            f.write(f"- **{score} pts** | {pretty(val)}\n")

        f.write("\n## 2. Top Cultural Symbol Recommendations\n")

        for score, sym, matched in symbol_scores[:3]:
            f.write(f"\n### {sym['name']}\n")
            f.write(f"**Culture:** {pretty(sym['culture'])} | **Match Score:** {score} points\n\n")
            f.write(f"**Documented Meaning:**\n{sym['meaning'].strip()}\n\n")
            f.write("**Why it matches:**\nIt perfectly embodies:")
            for m in matched:
                f.write(f"\n- *{pretty(m)}*")
            f.write("\n\n")
            if sym.get('design_notes'):
                f.write(f"**Kiarsy Design Note:** {sym['design_notes']}\n\n")
            f.write("---\n")

    print(f"✅ Report successfully generated at:\n{report_path}")

if __name__ == "__main__":
    main()
