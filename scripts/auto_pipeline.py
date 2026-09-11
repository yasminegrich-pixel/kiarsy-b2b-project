"""Kiarsy Auto-Pipeline: name + URL in -> tagged, scored, ranked company out."""
import sys, re, uuid, os
import numpy as np
import psycopg2, psycopg2.extras
from sentence_transformers import CrossEncoder, SentenceTransformer
from dossier_aggregator import build_dossier

# --- constants (calibrated for multilingual models) ---
TAG_REL_FLOOR = 0.30; ENTAIL_MIN = 0.60; MARGIN_MIN = 0.40
RELEVANCE_FLOOR = 0.20; RELATIVE_MARGIN = 0.05
MIN_EVID = 0.10; MIN_SHARED = 3; DISAG_CEIL = 0.5
TIER_W = {"Explicit": 1.0, "Strongly Supported": 0.7, "Possible": 0.4}
MAX_SENTENCES = 60

def softmax(x):
    e = np.exp(x - np.max(x)); return e / e.sum()
def cos(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def main(name, url, industry="", region=""):
    print("⏳ Loading multilingual models...")
    emb = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    nli = CrossEncoder("MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
    labels = list(nli.model.config.id2label.values())
    EI, CI = labels.index("entailment"), labels.index("contradiction")

    conn = psycopg2.connect(dbname="kiarsy_affinity", user="yasso")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT max(run_id) FROM scoring_runs")
    run_id = cur.fetchone()[0]
    if run_id is None:
        print("❌ No scoring run exists. Run scripts/scorer.py first."); return

    # ---------- 1. DOSSIER ----------
    print(f"\n🌐 Building dossier for {name} ...")
    d = build_dossier(name, url)
    text = "\n\n".join(t for texts in d.values() for t in texts)
    os.makedirs("reports", exist_ok=True)
    slug = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
    open(f"reports/dossier_{slug}.txt", "w", encoding="utf-8").write(text)
    print(f"   Dossier: {len(text)} chars saved to reports/dossier_{slug}.txt")

    sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 40]
    if len(sents) > MAX_SENTENCES:
        stride = len(sents) / MAX_SENTENCES
        sents = [sents[int(i * stride)] for i in range(MAX_SENTENCES)]
    print(f"   Scoring {len(sents)} sentences.")

    # ---------- 2. AUTO-TAG VALUES ----------
    print("\n🏷️  Auto-tagging the 15 Universal Values...")
    cur.execute("SELECT value_id, value_name FROM universal_values ORDER BY value_id")
    values = cur.fetchall()
    sent_embs = emb.encode(sents)
    tags = []
    for v in values:
        hyps = [f"This organization demonstrates {v['value_name']}.", v['value_name']]
        h_embs = emb.encode(hyps)
        rels = [max(cos(se, h) for h in h_embs) for se in sent_embs]
        best_e, best_sent = 0.0, ""
        for i in np.argsort(rels)[::-1][:3]:
            if rels[i] < TAG_REL_FLOOR: continue
            for h in hyps:
                p = softmax(nli.predict([(sents[i], h)])[0])
                e, c = float(p[EI]), float(p[CI])
                if e >= ENTAIL_MIN and (e - c) >= MARGIN_MIN and e > best_e:
                    best_e, best_sent = e, sents[i]
        if best_e >= 0.50:
            tier = "Explicit" if best_e >= 0.85 else "Strongly Supported" if best_e >= 0.65 else "Possible"
            tags.append((v['value_id'], v['value_name'], tier, best_sent, best_e))
            print(f"   ✅ {v['value_name'][:40]:<42} {tier:<20} {best_e:.2f}")
    if not tags:
        print("   ⚠️ No values passed the gate — company will rely on NLI scoring only.")

    # ---------- 3. SAVE COMPANY + VALUES ----------
    cur.execute("SELECT company_id FROM companies WHERE company_name = %s", (name,))
    row = cur.fetchone()
    if row:
        c_id = row['company_id']
        cur.execute("DELETE FROM company_values WHERE company_id=%s", (c_id,))
        cur.execute("DELETE FROM company_dimension_scores WHERE company_id=%s AND run_id=%s", (c_id, run_id))
        cur.execute("DELETE FROM company_symbol_affinity WHERE company_id=%s AND run_id=%s", (c_id, run_id))
    else:
        c_id = f"CO-{uuid.uuid4().hex[:4].upper()}"
        cur.execute("INSERT INTO companies (company_id, company_name, industry, country_region, company_summary) VALUES (%s,%s,%s,%s,%s)",
                    (c_id, name, industry, region, text[:2000]))
    for vid, vname, tier, quote, e in tags:
        cur.execute("INSERT INTO company_values (company_id, value_id, tier, evidence_summary) VALUES (%s,%s,%s,%s)",
                    (c_id, vid, tier, quote))
    conn.commit()
    print(f"\n💾 Saved company {c_id} with {len(tags)} value tags.")

    # ---------- 4. SCORE DIMENSIONS ----------
    print("\n📐 Scoring cultural dimensions...")
    cur.execute("SELECT dimension_id, low_anchor, high_anchor FROM dimensions WHERE dimension_type='values'")
    DIMS = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    anchor_embs = {dim: (emb.encode([lo])[0], emb.encode([hi])[0]) for dim, (lo, hi) in DIMS.items()}

    pairs, meta = [], []
    for si, s in enumerate(sents):
        rels = {dim: max(cos(sent_embs[si], lo), cos(sent_embs[si], hi)) for dim, (lo, hi) in anchor_embs.items()}
        weakest = min(rels.values())
        for dim, r in rels.items():
            if r >= RELEVANCE_FLOOR and (r >= weakest + RELATIVE_MARGIN or len(DIMS) == 1):
                pairs += [(s, DIMS[dim][0]), (s, DIMS[dim][1])]
                meta += [(si, dim, 'lo'), (si, dim, 'hi')]
    probs = []
    for i in range(0, len(pairs), 16):
        for row_ in nli.predict(pairs[i:i+16]):
            probs.append(softmax(row_))
    side_scores = {}
    for (si, dim, side), p in zip(meta, probs):
        side_scores.setdefault((si, dim), {})[side] = (float(p[EI]), float(p[CI]))

    cur.execute("SELECT value_id, dimension_id, position, loading FROM value_dimension_signatures")
    CROSSWALK = {(r[0], r[1]): (float(r[2]), float(r[3])) for r in cur.fetchall()}
    tag_dict = {t[0]: t[2] for t in tags}

    for dim in DIMS:
        contrib = []
        for si in range(len(sents)):
            sc = side_scores.get((si, dim))
            if not sc: continue
            if 'lo' in sc and 'hi' in sc:
                margin = (sc['hi'][0]-sc['hi'][1]) - (sc['lo'][0]-sc['lo'][1])
                pos = float(np.clip((margin+2)/4, 0, 1)); conf = float(np.clip(abs(margin)/2, 0, 1))
                if conf >= MIN_EVID:
                    contrib.append((pos, conf))
        if contrib:
            tw = sum(c for _, c in contrib)
            nli_pos = round(sum(p*c for p, c in contrib)/tw, 3)
            nli_conf = round(tw/len(contrib), 3)
            disagree = round(max(p for p, _ in contrib) - min(p for p, _ in contrib), 3) if len(contrib) > 1 else 0.0
        else:
            nli_pos = nli_conf = None; disagree = None
        num = den = 0.0
        for vid, tier in tag_dict.items():
            if (vid, dim) in CROSSWALK:
                pos, loading = CROSSWALK[(vid, dim)]
                w = TIER_W[tier] * loading; num += w*pos; den += w
        prior = round(num/den, 3) if den else None
        if nli_pos is not None and prior is not None:
            final = round(nli_conf*nli_pos + (1-nli_conf)*prior, 3); method = "blended"
        elif nli_pos is not None:
            final, method = nli_pos, "nli_only"
        elif prior is not None:
            final, method = prior, "prior_only"
        else:
            final, method = None, "unscored"
        if disagree is not None and disagree > DISAG_CEIL:
            final = None
        if final is not None:
            cur.execute("""INSERT INTO company_dimension_scores
                (company_id, dimension_id, run_id, nli_position, nli_confidence, off_topic_flag, prior_position, final_position, n_evidence, disagreement, method)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (c_id, dim, run_id, nli_pos, nli_conf, nli_pos is None, prior, final, len(contrib), disagree, method))
    conn.commit()

    # ---------- 5. AFFINITY MATCHES ----------
    print("\n🏆 Ranking symbols...")
    cur.execute("SELECT dimension_id, final_position FROM company_dimension_scores WHERE company_id=%s AND run_id=%s AND final_position IS NOT NULL", (c_id, run_id))
    c_vec = {r[0]: float(r[1]) for r in cur.fetchall()}
    cur.execute("SELECT symbol_id, dimension_id, position FROM symbol_dimension_scores WHERE run_id=%s", (run_id,))
    s_vecs = {}
    for r in cur.fetchall():
        s_vecs.setdefault(r[0], {})[r[1]] = float(r[2])
    cur.execute("SELECT symbol_id, culture_id FROM symbols")
    cult_of = {r[0]: r[1] for r in cur.fetchall()}

    matches = []
    for s_id, s_vec in s_vecs.items():
        shared = [d for d in c_vec if d in s_vec]
        if len(shared) < MIN_SHARED: continue
        a = np.array([c_vec[d] for d in shared]) - 0.5
        b = np.array([s_vec[d] for d in shared]) - 0.5
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0: continue
        raw = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        w = min(1.0, (len(shared) - MIN_SHARED + 1) / (len(DIMS) - MIN_SHARED + 1))
        matches.append((s_id, round(raw*w, 4), round(raw, 4), len(shared)))
    matches.sort(key=lambda x: x[1], reverse=True)
    counts = {}
    for s_id, adj, raw, shared in matches:
        cult = cult_of.get(s_id)
        counts[cult] = counts.get(cult, 0) + 1
        cur.execute("""INSERT INTO company_symbol_affinity
            (company_id, symbol_id, run_id, similarity, raw_similarity, shared_dimensions, evidence_weight, rank_in_culture)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
            (c_id, s_id, run_id, adj, raw, shared, round(adj/raw, 3) if raw else 0, counts[cult]))
    conn.commit()

    print(f"\n🎉 DONE! {name} is fully processed. Top 5 symbols:")
    cur.execute("SELECT s.symbol_name, a.similarity FROM company_symbol_affinity a JOIN symbols s ON s.symbol_id=a.symbol_id WHERE a.company_id=%s AND a.run_id=%s ORDER BY a.similarity DESC LIMIT 5", (c_id, run_id))
    for r in cur.fetchall():
        print(f"   {r[0]:<45} {float(r[1]):+.4f}")
    print("\n➡️  Open the dashboard and pick this company in the sidebar!")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "", sys.argv[4] if len(sys.argv) > 4 else "")
