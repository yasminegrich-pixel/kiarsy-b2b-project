#!/usr/bin/env python3
import yaml
import os
from pathlib import Path
import psycopg2

DATA_DIR = Path("data/cultures")  # relative to repo root, run this from the project folder

def main():
    conn = psycopg2.connect(
        dbname="kiarsy_affinity",
        user="yasso",
        password=os.environ.get("PGPASSWORD"),
        host="localhost",
        client_encoding="UTF8",
    )
    cur = conn.cursor()

    # Load the value name -> value_id mapping from the DB
    cur.execute("SELECT value_id, value_name FROM universal_values")
    value_lookup = {name: vid for vid, name in cur.fetchall()}

    print("Clearing old symbol data (placeholder/test symbols)...")
    cur.execute("DELETE FROM company_symbol_affinity;")
    cur.execute("DELETE FROM symbol_dimension_scores;")
    cur.execute("DELETE FROM symbol_value_matches;")
    cur.execute("DELETE FROM symbols;")
    conn.commit()

    total_symbols = 0
    total_matches = 0
    unmatched_values = set()
    culture_counts = {}

    for yaml_file in sorted(DATA_DIR.rglob("*.yaml")):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            continue

        symbol_id = f"{data['culture']}_{data['id']}"
        culture_id = data["culture"]
        sources_joined = "\n".join(data.get("sources", [])) if data.get("sources") else None

        cur.execute("""
            INSERT INTO symbols
                (symbol_id, symbol_name, culture_id, documented_meaning, sources, usage_status, usage_note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol_id) DO NOTHING
        """, (
            symbol_id,
            data.get("name", data["id"]),
            culture_id,
            data.get("meaning", "").strip(),
            sources_joined,
            data.get("usage", "open"),
            data.get("usage_note"),
        ))

        total_symbols += 1
        culture_counts[culture_id] = culture_counts.get(culture_id, 0) + 1

        for value_name in data.get("values", []):
            value_id = value_lookup.get(value_name)
            if value_id is None:
                unmatched_values.add(value_name)
                continue
            cur.execute("""
                INSERT INTO symbol_value_matches (symbol_id, value_id, strength)
                VALUES (%s, %s, 'core')
                ON CONFLICT DO NOTHING
            """, (symbol_id, value_id))
            total_matches += 1

    conn.commit()

    print(f"\nImported {total_symbols} symbols:")
    for culture, count in sorted(culture_counts.items()):
        print(f"  {culture}: {count}")
    print(f"Created {total_matches} symbol-value matches (strength defaulted to 'core').")

    if unmatched_values:
        print(f"\nWarning: {len(unmatched_values)} value name(s) in the yaml files did not match any universal_values entry:")
        for v in sorted(unmatched_values):
            print(f"  - {v}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()