#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import yaml
from pathlib import Path
import re

DATA_DIR = Path.home() / "kiarsy" / "data"

# Stems: "startup" catches startups, "innovat" catches innovation/innovative...
KEYWORDS = {
    "sustainab": "sustainability & green economy",
    "green": "sustainability & green economy",
    "environment": "sustainability & green economy",
    "climate": "sustainability & green economy",
    "woman": "women's empowerment",
    "women": "women's empowerment",
    "female": "women's empowerment",
    "youth": "youth development",
    "young": "youth development",
    "entrepreneur": "entrepreneurship & innovation",
    "startup": "entrepreneurship & innovation",
    "innovat": "entrepreneurship & innovation",
    "partner": "collaboration & partnership",
    "collaborat": "collaboration & partnership",
    "refugee": "social inclusion of refugees/IDPs",
    "displaced": "social inclusion of refugees/IDPs",
    "impact": "impact & accountability",
    "accountab": "impact & accountability",
    "leader": "regional leadership",
    "region": "regional leadership"
}

def fetch(url):
    print(f"Scraping {url}...")
    response = requests.get(url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text().lower()

def main():
    urls = ["https://flat6labs.com/", "https://flat6labs.com/about/"]
    text = " ".join(fetch(u) for u in urls)

    counts = {}
    for stem, value in KEYWORDS.items():
        count = len(re.findall(r'\b' + stem + r'[a-z]*', text))
        if count > 0:
            counts[value] = counts.get(value, 0) + count

    # Scaling: every 3 mentions = 1 point, capped at 10
    weighted = {val: min(10, max(1, c // 3)) for val, c in counts.items()}

    company_data = {
        'id': 'flat6labs',
        'name': 'Flat6Labs',
        'channel_1': {
            'source': 'Automated Web Scraping',
            'values': weighted
        }
    }

    out_file = DATA_DIR / "companies" / "flat6labs.yaml"
    with open(out_file, 'w') as f:
        yaml.dump(company_data, f, sort_keys=False)

    print("Raw counts:", counts)
    print("Weights:", weighted)

if __name__ == "__main__":
    main()
