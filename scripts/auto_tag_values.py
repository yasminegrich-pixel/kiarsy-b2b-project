"""
Kiarsy - Automatic Value Tagging
Detects which of the 15 Universal Values are present in a company dossier.
"""

import yaml
import re
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
import torch

# -------------------------------------------------
# Load the 15 Universal Values
# -------------------------------------------------
VALUES_FILE = Path("data/values.yaml")

with open(VALUES_FILE, "r", encoding="utf-8") as f:
    VALUES = yaml.safe_load(f)["values"]

print(f"Loaded {len(VALUES)} universal values.")

# -------------------------------------------------
# Load embedding model (multilingual)
# -------------------------------------------------
print("Loading embedding model (this may take a few seconds)...")
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Pre-compute embeddings for all values
value_embeddings = model.encode(VALUES, convert_to_tensor=True)


def split_into_chunks(text: str, max_chars: int = 600) -> list[str]:
    """Split long text into smaller chunks for better matching."""
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
    """
    Returns a list of detected values with confidence scores.
    """
    chunks = split_into_chunks(text)
    print(f"Analyzing {len(chunks)} text chunks...")

    chunk_embeddings = model.encode(chunks, convert_to_tensor=True)

    # Compute similarity between every chunk and every value
    similarities = util.cos_sim(chunk_embeddings, value_embeddings)

    # For each value, keep the highest similarity found
    results = []
    for idx, value in enumerate(VALUES):
        max_score = float(torch.max(similarities[:, idx]))
        results.append({
            "value": value,
            "score": round(max_score, 3)
        })

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Assign tiers
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
            continue  # too weak, skip

        tagged.append({
            "value": r["value"],
            "score": score,
            "tier": tier
        })

    return tagged


# -------------------------------------------------
# Main test
# -------------------------------------------------
if __name__ == "__main__":
    dossier_path = Path("reports/dossier_wwf_tunisia_v2.txt")

    if not dossier_path.exists():
        print("Dossier file not found. Run the scraper first.")
        exit()

    text = dossier_path.read_text(encoding="utf-8")
    print(f"\nDossier loaded: {len(text):,} characters\n")

    tagged = tag_values(text)

    print("=" * 60)
    print("DETECTED VALUES FOR WWF TUNISIA")
    print("=" * 60)

    for i, item in enumerate(tagged, 1):
        print(f"{i:2}. [{item['tier']:<18}] {item['value']:<45} (score: {item['score']})")

    print("\nDone.")
