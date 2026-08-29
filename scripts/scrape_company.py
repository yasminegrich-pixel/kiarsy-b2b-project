#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import yaml
from pathlib import Path
import re
import sys

DATA_DIR = Path.home() / "kiarsy" / "data"

# The new Universal 15 Keyword Dictionary
KEYWORDS = {
    "Women's Empowerment & Gender Equity": ["woman", "women", "female", "gender", "equity", "girl", "feminist", "maternity"],
    "Diversity, Inclusion & Minority Rights": ["diversity", "inclusion", "minority", "marginalized", "accessible", "belonging", "dei"],
    "Refugee Support & Immigrant Inclusion": ["refugee", "displaced", "immigrant", "migration", "asylum", "integration"],
    "Youth Development & Next-Gen Education": ["youth", "young", "student", "education", "mentor", "next-gen", "child", "school"],
    "Environmental Sustainability & Climate Action": ["sustainab", "green", "climate", "environment", "eco", "carbon", "circular", "nature", "planet"],
    "Entrepreneurship & Innovation": ["entrepreneur", "startup", "innovat", "tech", "scale", "pivot", "founder", "agility", "disrupt"],
    "Collaboration, Partnerships & Ecosystems": ["partner", "collaborat", "ecosystem", "network", "joint", "alliance", "community", "co-"],
    "Leadership, Governance & Authority": ["leader", "governance", "board", "executive", "authority", "director", "vision", "chief"],
    "Trust, Security & Risk Management": ["trust", "secur", "risk", "privacy", "protect", "cyber", "safety", "compliance", "data"],
    "Justice, Human Rights & Transparency": ["justice", "human rights", "transparent", "fair", "legal", "ethical", "accountab", "equity"],
    "Care, Health & Community Nurturing": ["health", "care", "well-being", "mental", "nurture", "heal", "wellness", "patient"],
    "Heritage, Craftsmanship & Legacy": ["heritage", "craft", "legacy", "artisan", "tradition", "history", "culture", "handmade"],
    "Resilience, Endurance & Crisis Survival": ["resilien", "endure", "survive", "crisis", "hardship", "tough", "adapt", "overcome"],
    "Economic Growth & Abundance": ["growth", "wealth", "econom", "finance", "prosper", "revenue", "abundance", "market", "profit"],
    "Transformation, Renewal & Change Management": ["transform", "renew", "change", "shift", "evolut", "transition", "future", "impact"]
}

def fetch(url):
    print(f"Scraping {url}...")
    try:
        response = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup.get_text().lower()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def main():
    # Allow passing URL and Name as arguments, or default to Flat6Labs
    if len(sys.argv) >= 3:
        company_id = sys.argv[1].lower().replace(" ", "_")
        company_name = sys.argv[1]
        urls = sys.argv[2:]
    else:
        company_id = "flat6labs"
        company_name = "Flat6Labs"
        urls = ["https://flat6labs.com/", "https://flat6labs.com/about/"]

    text = " ".join(fetch(u) for u in urls)

    counts = {}
    for value, stems in KEYWORDS.items():
        total_count = 0
        for stem in stems:
            # Count occurrences using regex to match word stems
            total_count += len(re.findall(r'\b' + stem + r'[a-z]*', text))
        if total_count > 0:
            counts[value] = total_count

    # Scaling: every 5 mentions = 1 point, capped at 10
    weighted = {val: min(10, max(1, c // 5)) for val, c in counts.items()}

    company_data = {
        'id': company_id,
        'name': company_name,
        'channel_1': {
            'source': 'Automated Web Scraping',
            'values': weighted
        }
    }

    out_file = DATA_DIR / "companies" / f"{company_id}.yaml"
    with open(out_file, 'w') as f:
        yaml.dump(company_data, f, sort_keys=False)

    print(f"\n✅ Scraped and saved to {out_file.name}")
    print("Detected Universal Values & Weights:")
    for val, weight in sorted(weighted.items(), key=lambda x: x[1], reverse=True):
        print(f"  [{weight:>2} pts] {val} (Raw mentions: {counts[val]})")

if __name__ == "__main__":
    main()
