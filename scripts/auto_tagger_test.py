import psycopg2, re, sys
import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

print("⏳ Loading multilingual AI models (first run downloads ~1 GB)...")
emb = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
nli = CrossEncoder("MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")

# Read label order from the model itself (no hardcoded indices)
labels = list(nli.model.config.id2label.values())
EI, CI = labels.index("entailment"), labels.index("contradiction")
print(f"   Label order detected: {labels}")

REL_FLOOR = 0.35      # embedding relevance gate (was 0.10 -> too loose)
ENTAIL_MIN = 0.60     # minimum entailment probability
MARGIN_MIN = 0.40     # entailment must beat contradiction decisively

conn = psycopg2.connect(dbname="kiarsy_affinity", user="yasso")
cur = conn.cursor()
cur.execute("SELECT value_id, value_name, COALESCE(definition,'') FROM universal_values ORDER BY value_id")
VALUES = [(r[0], r[1], r[2]) for r in cur.fetchall()]
conn.close()

if len(sys.argv) > 1:
    DOSSIER = open(sys.argv[1], encoding="utf-8").read()
else:
    DOSSIER = """
Sopra HR Software is a French company specializing in human resources software.
The company is committed to reducing its carbon footprint and has achieved net-zero emissions by 2025.
Sopra HR places a strong emphasis on inclusivity, ensuring equal pay for men and women across all its European offices.
The company invests heavily in youth development, partnering with local universities to train 500 students annually in AI and cloud computing.
Sopra HR's core mission is to accelerate the positive digital transformation of HR, putting humans at the heart of performance.
"""

def softmax(x):
    e = np.exp(x - np.max(x)); return e / e.sum()

sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', DOSSIER) if len(s.strip()) > 20]
sent_embs = emb.encode(sentences)

print(f"\n{'Value':<38}{'Rel':>6}{'Entail':>8}{'Margin':>8}  Tier")
print("-" * 74)
proposals = []
for v_id, v_name, v_def in VALUES:
    hyp  = f"This organization demonstrates {v_name}."
    hyp2 = v_def if v_def else hyp
    h_embs = emb.encode([hyp, hyp2])
    rels = [max(float(np.dot(se, h) / (np.linalg.norm(se) * np.linalg.norm(h))) for h in h_embs)
            for se in sent_embs]
    order = np.argsort(rels)[::-1][:3]

    best_e, best_m, best_sent, best_rel = 0.0, 0.0, "", 0.0
    for i in order:
        if rels[i] < REL_FLOOR:          # <- the gate that kills fabricated entailment
            continue
        for h in (hyp, hyp2):
            p = softmax(nli.predict([(sentences[i], h)])[0])
            e, c = float(p[EI]), float(p[CI])
            if e >= ENTAIL_MIN and (e - c) >= MARGIN_MIN and e > best_e:
                best_e, best_m, best_sent, best_rel = e, e - c, sentences[i], rels[i]

    tier = ("Explicit" if best_e >= 0.85 else
            "Strongly Supported" if best_e >= 0.65 else
            "Possible" if best_e >= 0.50 else "-")
    print(f"{v_name[:36]:<38}{best_rel:>6.2f}{best_e:>8.2f}{best_m:>8.2f}  {tier}")
    if tier != "-":
        proposals.append((v_name, tier, best_sent, best_e))

print("\n" + "=" * 74)
print("🤖 AUTO-TAGGER PROPOSALS (v3 — gated)")
print("=" * 74)
for v_name, tier, sent, score in sorted(proposals, key=lambda x: -x[3]):
    print(f"\n✅ {v_name} — {tier} (conf {score:.2f})")
    print(f"   \"{sent}\"")
if not proposals:
    print("None — paste the table and we'll tune the floor.")
