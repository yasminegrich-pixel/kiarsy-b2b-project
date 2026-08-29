#!/usr/bin/env python3
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path.home() / "kiarsy" / "data"
OUT_DIR = Path.home() / "kiarsy" / "output"

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def pretty(text):
    if not text: return ""
    return text[0].upper() + text[1:]

def generate_report(company_file, symbols):
    company_data = load_yaml(company_file)
    company_id = company_data['id']
    
    # Check if a B2B test file exists for this company
    test_file = DATA_DIR / "tests" / f"{company_id}_test.yaml"
    test_data = load_yaml(test_file) if test_file.exists() else {}

    merged_values = {}
    for val, weight in company_data.get('channel_1', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight
    for val, weight in test_data.get('channel_2', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight

    top_values = sorted(merged_values.items(), key=lambda x: x[1], reverse=True)

    scored_by_culture = defaultdict(list)
    for sym in symbols:
        score = 0
        matched = []
        for v in sym.get('values', []):
            if v in merged_values:
                score += merged_values[v]
                matched.append(v)
        culture = sym.get('culture', 'unknown')
        scored_by_culture[culture].append((score, sym, matched))

    for culture in scored_by_culture:
        scored_by_culture[culture].sort(reverse=True, key=lambda x: x[0])

    today = datetime.now().strftime("%Y-%m-%d")
    report_path = OUT_DIR / f"{company_id}_recommendation.md"

    culture_order = ['amazigh', 'amerindienne', 'subsaharienne']

    with open(report_path, 'w') as f:
        f.write(f"# KIARSY Design Recommendation: {company_data['name']}\n")
        f.write(f"*Generated on {today}*\n\n")

        f.write("## 1. Company Value Profile\n")
        f.write(f"Source: {company_data.get('channel_1', {}).get('source', 'Unknown')}\n\n")
        for val, score in top_values[:5]:
            f.write(f"- **{score} pts** | {pretty(val)}\n")

        f.write("\n## 2. Top Cultural Symbol Recommendations (3 per Culture)\n")

        for culture in culture_order:
            if culture not in scored_by_culture: continue
            f.write(f"\n### 🌍 Culture: {pretty(culture)}\n")
            top_3_culture = scored_by_culture[culture][:3]
            
            for score, sym, matched in top_3_culture:
                f.write(f"\n#### {sym['name']}\n")
                f.write(f"**Match Score:** {score} points\n\n")
                f.write(f"**Documented Meaning:**\n{sym['meaning'].strip()}\n\n")
                f.write("**Why it matches:**\nIt perfectly embodies:")
                if matched:
                    for m in matched:
                        f.write(f"\n- *{pretty(m)}*")
                else:
                    f.write("\n- *No direct value matches.*")
                f.write("\n\n")
                if sym.get('design_notes'):
                    f.write(f"**Kiarsy Design Note:** {sym['design_notes']}\n\n")
                f.write("---\n")
    print(f"✅ Generated: {report_path.name}")

def main():
    symbols = []
    for file in (DATA_DIR / "cultures").rglob("*.yaml"):
        data = load_yaml(file)
        if data: symbols.append(data)
        
    companies_dir = DATA_DIR / "companies"
    company_files = list(companies_dir.glob("*.yaml"))
    
    print(f"Generating reports for {len(company_files)} companies...")
    for cf in company_files:
        generate_report(cf, symbols)

if __name__ == "__main__":
    main()
