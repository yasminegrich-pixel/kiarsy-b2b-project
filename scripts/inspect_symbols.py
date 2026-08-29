#!/usr/bin/env python3
import yaml
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path.home() / "kiarsy" / "data"

def load_symbols():
    symbols = []
    for file in (DATA_DIR / "cultures").rglob("*.yaml"):
        with open(file, 'r') as f:
            data = yaml.safe_load(f)
        if data:
            symbols.append(data)
    return symbols

def main():
    symbols = load_symbols()

    # Group by culture
    by_culture = defaultdict(list)
    for s in symbols:
        by_culture[s.get("culture", "unknown")].append(s)

    # Track value coverage
    value_count = defaultdict(int)

    for culture in sorted(by_culture.keys()):
        group = sorted(by_culture[culture], key=lambda x: x.get("name", ""))
        print(f"\n{'='*70}")
        print(f"  CULTURE: {culture.upper()}  ({len(group)} symbols)")
        print(f"{'='*70}")
        for s in group:
            usage = s.get("usage", "open").upper()
            flag = "🔒" if usage == "RESTRICTED" else "  "
            print(f"\n{flag} {s.get('name', 'Unnamed')}")
            for v in s.get("values", []):
                value_count[v] += 1
                print(f"      • {v}")

    # Coverage summary
    print(f"\n{'='*70}")
    print(f"  VALUE COVERAGE SUMMARY")
    print(f"{'='*70}")

    all_values = yaml.safe_load((DATA_DIR / "values.yaml").read_text()).get("values", [])
    for v in all_values:
        count = value_count.get(v, 0)
        marker = "✅" if count > 0 else "❌ MISSING"
        print(f"  {marker:12} [{count:>2} symbols] {v}")

    # Unused values detection
    unused = [v for v in all_values if value_count.get(v, 0) == 0]
    if unused:
        print(f"\n⚠️  {len(unused)} value(s) have NO symbols yet:")
        for v in unused:
            print(f"      - {v}")

if __name__ == "__main__":
    main()
