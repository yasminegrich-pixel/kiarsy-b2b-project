#!/usr/bin/env python3
import yaml
from pathlib import Path

# Define the path to our kiarsy data folder
DATA_DIR = Path.home() / "kiarsy" / "data"

def load_symbols():
    symbols = []
    # Recursively find all .yaml files inside the cultures folder
    for file in (DATA_DIR / "cultures").rglob("*.yaml"):
        with open(file, 'r') as f:
            data = yaml.safe_load(f)
            if data:
                symbols.append(data)
    return symbols

if __name__ == "__main__":
    syms = load_symbols()
    cultures = sorted(set(s["culture"] for s in syms))
    print(f"Loaded {len(syms)} symbols from {len(cultures)} culture(s): {cultures}")
    for s in syms:
        print(f"- {s['name']} -> {len(s['values'])} values")
