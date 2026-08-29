#!/usr/bin/env python3
"""Migrate all Kiarsy data files from old values to the new Universal 15."""
from pathlib import Path

DATA_DIR = Path.home() / "kiarsy" / "data"

VALUE_MAP = {
    "inclusivity & opportunity": "Diversity, Inclusion & Minority Rights",
    "regional leadership": "Leadership, Governance & Authority",
    "movement toward sustainability": "Transformation, Renewal & Change Management",
    "entrepreneurship & innovation": "Entrepreneurship & Innovation",
    "collaboration & partnership": "Collaboration, Partnerships & Ecosystems",
    "women's empowerment": "Women's Empowerment & Gender Equity",
    "impact & accountability": "Justice, Human Rights & Transparency",
    "sustainability & green economy": "Environmental Sustainability & Climate Action",
    "social inclusion of refugees/IDPs": "Refugee Support & Immigrant Inclusion",
    "youth development": "Youth Development & Next-Gen Education",
}

def migrate_file(file):
    text = file.read_text()
    original = text
    for old_val, new_val in VALUE_MAP.items():
        text = text.replace(f'- "{old_val}"', f'- "{new_val}"')
        text = text.replace(f'"{old_val}":', f'"{new_val}":')
        text = text.replace(f'value: "{old_val}"', f'value: "{new_val}"')
        text = text.replace(f'{old_val}:', f'{new_val}:')
    if text != original:
        file.write_text(text)
        return True
    return False

def main():
    migrated = 0
    for dir_name in ["cultures", "companies", "tests"]:
        dir_path = DATA_DIR / dir_name
        if not dir_path.exists():
            continue
        for file in dir_path.rglob("*.yaml"):
            if migrate_file(file):
                migrated += 1
                print(f"  ✓ {file.relative_to(DATA_DIR)}")
    print(f"\n✅ Migrated {migrated} files to the Universal 15 Value Framework.")

if __name__ == "__main__":
    main()
