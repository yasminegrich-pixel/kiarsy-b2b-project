#!/usr/bin/env python3
import yaml
from pathlib import Path

DATA_DIR = Path.home() / "kiarsy" / "data"

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

def main():
    # 1. Load all cultural symbols
    symbols = []
    for file in (DATA_DIR / "cultures").rglob("*.yaml"):
        data = load_yaml(file)
        if data:
            symbols.append(data)

    # 2. Load company data (Flat6Labs)
    company_data = load_yaml(DATA_DIR / "companies" / "flat6labs.yaml")
    test_data = load_yaml(DATA_DIR / "tests" / "flat6labs_test.yaml")

    # 3. Merge Channel 1 and Channel 2
    merged_values = {}
    
    # Add Channel 1 weights
    for val, weight in company_data.get('channel_1', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight
        
    # Add Channel 2 weights
    for val, weight in test_data.get('channel_2', {}).get('values', {}).items():
        merged_values[val] = merged_values.get(val, 0) + weight

    # Sort company values to see what matters most to them
    top_values = sorted(merged_values.items(), key=lambda x: x[1], reverse=True)

    print(f"--- {company_data['name']} Merged Profile ---")
    print("Top 5 values (Channel 1 + Channel 2 combined):")
    for val, score in top_values[:5]:
        print(f"  {score:>2} pts | {val}")

    print("\n--- Top Matching Symbols ---")

    # 4. Score symbols against the company's values
    symbol_scores = []
    for sym in symbols:
        score = 0
        matched = []
        for v in sym.get('values', []):
            if v in merged_values:
                score += merged_values[v]
                matched.append(v)
        symbol_scores.append((score, sym['name'], sym['culture'], matched))

    # Sort symbols by highest score
    symbol_scores.sort(reverse=True, key=lambda x: x[0])

    # 5. Print the winning recommendations
    for score, name, culture, matched in symbol_scores[:3]:
        print(f"\n[{culture}] {name} (Score: {score})")
        print(f"  Matches values: {', '.join(matched)}")

if __name__ == "__main__":
    main()
