#!/usr/bin/env python3
"""Apply the corrected value assignments to all 56 symbols."""
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path.home() / "kiarsy" / "data"

CORRECTIONS = {
    # ===== AMAZIGH =====
    "afus": ["Women's Empowerment & Gender Equity", "Trust, Security & Risk Management"],
    "aslem": ["Trust, Security & Risk Management"],
    "ayyur": ["Women's Empowerment & Gender Equity", "Transformation, Renewal & Change Management"],
    "azemmur": ["Economic Growth & Abundance", "Environmental Sustainability & Climate Action"],
    "crescent-star": ["Transformation, Renewal & Change Management"],
    "farfattou": ["Women's Empowerment & Gender Equity", "Transformation, Renewal & Change Management"],
    "izem": ["Leadership, Governance & Authority", "Resilience, Endurance & Crisis Survival"],
    "hanneton": ["Transformation, Renewal & Change Management"],
    "tafukt": ["Economic Growth & Abundance", "Environmental Sustainability & Climate Action"],
    "tanit": ["Women's Empowerment & Gender Equity", "Care, Health & Community Nurturing"],
    "tazerzit": ["Women's Empowerment & Gender Equity", "Heritage, Craftsmanship & Legacy"],
    "agadez-cross": ["Youth Development & Next-Gen Education", "Transformation, Renewal & Change Management", "Heritage, Craftsmanship & Legacy"],
    "anchor": ["Trust, Security & Risk Management", "Resilience, Endurance & Crisis Survival"],
    "lozenge": ["Women's Empowerment & Gender Equity", "Care, Health & Community Nurturing"],
    "eye": ["Trust, Security & Risk Management"],
    "frog": ["Environmental Sustainability & Climate Action", "Transformation, Renewal & Change Management"],
    "key": ["Refugee Support & Immigrant Inclusion", "Heritage, Craftsmanship & Legacy"],
    "ram": ["Leadership, Governance & Authority"],
    "scorpion": ["Resilience, Endurance & Crisis Survival", "Trust, Security & Risk Management"],
    "serpent": ["Transformation, Renewal & Change Management", "Trust, Security & Risk Management"],
    "spider": ["Women's Empowerment & Gender Equity", "Collaboration, Partnerships & Ecosystems"],
    "swallow": ["Transformation, Renewal & Change Management", "Refugee Support & Immigrant Inclusion"],
    "weaving-comb": ["Women's Empowerment & Gender Equity", "Heritage, Craftsmanship & Legacy"],
    "seed-field": ["Economic Growth & Abundance", "Environmental Sustainability & Climate Action"],
    "world-tree": ["Environmental Sustainability & Climate Action", "Youth Development & Next-Gen Education"],
    "zigzag": ["Transformation, Renewal & Change Management", "Economic Growth & Abundance"],
    "bee": ["Collaboration, Partnerships & Ecosystems", "Entrepreneurship & Innovation"],
    "yaz": ["Diversity, Inclusion & Minority Rights", "Justice, Human Rights & Transparency"],
    # ===== AMERINDIENNE =====
    "kokopelli": ["Economic Growth & Abundance", "Transformation, Renewal & Change Management"],
    "broken-arrow": ["Collaboration, Partnerships & Ecosystems"],
    "butterfly": ["Transformation, Renewal & Change Management", "Women's Empowerment & Gender Equity"],
    "eagle": ["Leadership, Governance & Authority", "Justice, Human Rights & Transparency"],
    "hogan": ["Refugee Support & Immigrant Inclusion", "Care, Health & Community Nurturing", "Heritage, Craftsmanship & Legacy"],
    "medicine-wheel": ["Diversity, Inclusion & Minority Rights", "Care, Health & Community Nurturing"],
    "migration-spiral": ["Refugee Support & Immigrant Inclusion", "Transformation, Renewal & Change Management"],
    "morning-star": ["Transformation, Renewal & Change Management", "Leadership, Governance & Authority"],
    "snake": ["Environmental Sustainability & Climate Action", "Transformation, Renewal & Change Management"],
    "sun-symbol": ["Economic Growth & Abundance", "Environmental Sustainability & Climate Action"],
    "three-sisters": ["Collaboration, Partnerships & Ecosystems", "Environmental Sustainability & Climate Action"],
    "thunderbird": ["Leadership, Governance & Authority", "Trust, Security & Risk Management"],
    "turtle": ["Environmental Sustainability & Climate Action", "Trust, Security & Risk Management"],
    # ===== SUBSAHARIENNE =====
    "adinkrahene": ["Leadership, Governance & Authority", "Heritage, Craftsmanship & Legacy"],
    "akoko-nan": ["Care, Health & Community Nurturing", "Youth Development & Next-Gen Education"],
    "akoma": ["Care, Health & Community Nurturing", "Collaboration, Partnerships & Ecosystems"],
    "ananse-ntontan": ["Entrepreneurship & Innovation", "Collaboration, Partnerships & Ecosystems"],
    "asase-ye-duru": ["Environmental Sustainability & Climate Action", "Care, Health & Community Nurturing"],
    "aya": ["Resilience, Endurance & Crisis Survival"],
    "boa-me": ["Collaboration, Partnerships & Ecosystems"],
    "denkyem": ["Entrepreneurship & Innovation", "Leadership, Governance & Authority"],
    "duafe": ["Women's Empowerment & Gender Equity", "Care, Health & Community Nurturing"],
    "siamese-crocs": ["Diversity, Inclusion & Minority Rights", "Collaboration, Partnerships & Ecosystems", "Justice, Human Rights & Transparency"],
    "hwe-mu-dua": ["Justice, Human Rights & Transparency", "Entrepreneurship & Innovation"],
    "mpatapo": ["Collaboration, Partnerships & Ecosystems", "Resilience, Endurance & Crisis Survival"],
    "nkyinkyim": ["Entrepreneurship & Innovation", "Transformation, Renewal & Change Management"],
    "nyansapo": ["Leadership, Governance & Authority", "Entrepreneurship & Innovation"],
    "sankofa": ["Heritage, Craftsmanship & Legacy", "Youth Development & Next-Gen Education"],
}

def replace_values_block(text, new_values):
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.rstrip() == 'values:':
            result.append('values:')
            for v in new_values:
                result.append(f'  - "{v}"')
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith('- '):
                i += 1
            continue
        result.append(line)
        i += 1
    return '\n'.join(result)

def get_id(text):
    for line in text.split('\n'):
        if line.startswith('id:'):
            return line.split(':', 1)[1].strip()
    return None

def main():
    updated = 0
    for file in sorted((DATA_DIR / "cultures").rglob("*.yaml")):
        text = file.read_text()
        sym_id = get_id(text)
        if sym_id in CORRECTIONS:
            file.write_text(replace_values_block(text, CORRECTIONS[sym_id]))
            updated += 1
            print(f"  ✓ {sym_id:18} -> {len(CORRECTIONS[sym_id])} value(s)")

    print(f"\n✅ Updated {updated} / {len(CORRECTIONS)} symbols.")

    # Coverage check
    present = {get_id(f.read_text()) for f in (DATA_DIR / "cultures").rglob("*.yaml")}
    missing = set(CORRECTIONS) - present
    if missing:
        print(f"❌ Not found in files: {missing}")

    # Distribution
    dist = defaultdict(int)
    for vals in CORRECTIONS.values():
        for v in vals:
            dist[v] += 1
    print(f"\n--- NEW VALUE DISTRIBUTION ---")
    for v, c in sorted(dist.items(), key=lambda x: -x[1]):
        print(f"  [{c:>2}] {v}")

if __name__ == "__main__":
    main()
