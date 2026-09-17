"""
Kiarsy - Process Company (Baby Step 5)
--------------------------------------
1. Scrapes the company
2. Automatically detects values
3. Saves company + values into the database
"""

import sys
import yaml
import re
import uuid
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import torch
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import os

# Import the scraper
from dossier_v2 import build_dossier

load_dotenv()

# -------------------------------------------------
# Database connection
# -------------------------------------------------
def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "kiarsy_affinity"),
        user=os.getenv("DB_USER", "yasso"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )

# -------------------------------------------------
# Load the 15 Universal Values
# -------------------------------------------------
VALUES_FILE = Path("data/values.yaml")
with open(VALUES_FILE, "r", encoding="utf-8") as f:
    VALUES = yaml.safe_load(f)["values"]

# -------------------------------------------------
# Load embedding model
# -------------------------------------------------
print("Loading AI model...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
value_embeddings = model.encode(VALUES, convert_to_tensor=True)


def split_into_chunks(text: str, max_chars: int = 600) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) < max_chars:
            current += " " + sent
        else:
            if current.strip():
                chunks.append(current.strip())
            current = sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


def tag_values(text: str, top_k: int = 8) -> list[dict]:
    chunks = split_into_chunks(text)
    chunk_embeddings = model.encode(chunks, convert_to_tensor=True)
    similarities = util.cos_sim(chunk_embeddings, value_embeddings)

    results = []
    for idx, value in enumerate(VALUES):
        max_score = float(torch.max(similarities[:, idx]))
        results.append({"value": value, "score": round(max_score, 3)})

    results.sort(key=lambda x: x["score"], reverse=True)

    tagged = []
    for r in results[:top_k]:
        score = r["score"]
        if score >= 0.42:
            tier = "Explicit"
        elif score >= 0.32:
            tier = "Strongly Supported"
        elif score >= 0.25:
            tier = "Possible"
        else:
            continue

        tagged.append({
            "value": r["value"],
            "score": score,
            "tier": tier
        })
    return tagged


def save_to_database(company_name: str, website_url: str, full_text: str, tagged_values: list[dict]):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    try:
        # Check if company already exists
        cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (company_name,))
        row = cur.fetchone()

        if row:
            company_id = row["company_id"]
            print(f"↻ Updating existing company: {company_id}")
            # Clean old values
            cur.execute("DELETE FROM company_values WHERE company_id = %s", (company_id,))
            cur.execute("""
                UPDATE companies 
                SET company_summary = %s, websites = %s
                WHERE company_id = %s
            """, (full_text[:3000], website_url, company_id))
        else:
            company_id = f"CO-{uuid.uuid4().hex[:6].upper()}"
            print(f"➕ Creating new company: {company_id}")
            cur.execute("""
                INSERT INTO companies (company_id, company_name, websites, company_summary)
                VALUES (%s, %s, %s, %s)
            """, (company_id, company_name, website_url, full_text[:3000]))

        # Get value_id mapping
        cur.execute("SELECT value_id, value_name FROM universal_values")
        value_map = {r["value_name"]: r["value_id"] for r in cur.fetchall()}

        # Insert detected values
        for item in tagged_values:
            value_name = item["value"]
            tier = item["tier"]
            value_id = value_map.get(value_name)

            if value_id:
                cur.execute("""
                    INSERT INTO company_values (company_id, value_id, tier, evidence_summary)
                    VALUES (%s, %s, %s, %s)
                """, (company_id, value_id, tier, f"Auto-detected (score: {item['score']})"))
            else:
                print(f"⚠️  Value not found in database: {value_name}")

        conn.commit()
        print(f"✅ Saved {len(tagged_values)} values to database.")
        return company_id

    except Exception as e:
        conn.rollback()
        print(f"❌ Database error: {e}")
        return None
    finally:
        cur.close()
        conn.close()


def main(company_name: str, website_url: str):
    print("\n" + "="*60)
    print(f"PROCESSING: {company_name}")
    print("="*60)

    # 1. Build dossier
    dossier = build_dossier(company_name, website_url)
    full_text = dossier["full_text"]

    # Save dossier file
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    safe_name = re.sub(r'[^a-z0-9]+', '_', company_name.lower()).strip('_')
    dossier_file = reports_dir / f"dossier_{safe_name}.txt"
    dossier_file.write_text(full_text, encoding="utf-8")
    print(f"\n📄 Dossier saved → {dossier_file}")

    # 2. Automatic value tagging
    print("\n🏷️  Detecting values...")
    tagged = tag_values(full_text)

    print("\n" + "="*60)
    print("DETECTED VALUES")
    print("="*60)
    for i, item in enumerate(tagged, 1):
        print(f"{i:2}. [{item['tier']:<18}] {item['value']:<45} ({item['score']})")

    # 3. Save to database
    print("\n💾 Saving to database...")
    company_id = save_to_database(company_name, website_url, full_text, tagged)

    if company_id:
        print(f"\n✅ SUCCESS! Company is now in the database.")
        print(f"   → Open the Streamlit app and select \"{company_name}\" in the sidebar.")
    else:
        print("\n❌ Failed to save to database.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print('  python scripts/process_company.py "Company Name" "https://website.com"')
        sys.exit(1)

    name = sys.argv[1]
    url = sys.argv[2]
    main(name, url)
