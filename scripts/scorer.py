import psycopg2
import psycopg2.extras
from sentence_transformers import CrossEncoder, SentenceTransformer
import numpy as np
import re
import torch
import gc
torch.set_num_threads(1)

print("Loading AI models (this takes ~30 seconds)...", flush=True)
nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-base")
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

RELEVANCE_FLOOR = 0.20
RELATIVE_MARGIN = 0.05
MIN_EVIDENCE_CONFIDENCE = 0.10
MIN_SHARED_DIMS = 3
DISAGREEMENT_CEILING = 0.5
TIER_WEIGHTS = {"Explicit": 1.0, "Strongly Supported": 0.7, "Possible": 0.4}

def nli_probs(a, b):
    scores = nli_model.predict([(a, b)])[0]
    exp_scores = np.exp(scores - np.max(scores))
    probs = exp_scores / exp_scores.sum()
    return float(probs[0]), float(probs[1]), float(probs[2])

def cos_sim(u, v):
    return float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))

def relevance_scores(unit_text, dimensions: dict):
    dim_order = list(dimensions.keys())
    all_texts = [unit_text]
    for dim_id in dim_order:
        low, high = dimensions[dim_id]
        all_texts += [low, high]
    embeddings = embed_model.encode(all_texts)
    u = embeddings[0]
    out = {}
    for i, dim_id in enumerate(dim_order):
        lo, hi = embeddings[1 + 2 * i], embeddings[2 + 2 * i]
        out[dim_id] = max(cos_sim(u, lo), cos_sim(u, hi))
    return out

def nli_score_all(unit_text, dimensions: dict):
    rel = relevance_scores(unit_text, dimensions)
    weakest = min(rel.values()) if rel.values() else 0
    results = {}
    for dim_id, (low, high) in dimensions.items():
        r = rel[dim_id]
        on_topic = (r >= RELEVANCE_FLOOR) and (r >= weakest + RELATIVE_MARGIN or len(dimensions) == 1)
        if not on_topic:
            results[dim_id] = {"nli_position": None, "nli_confidence": 0.0, "relevance": round(r, 3)}
            continue
        contra_low, entail_low, _ = nli_probs(unit_text, low)
        contra_high, entail_high, _ = nli_probs(unit_text, high)
        margin = (entail_high - contra_high) - (entail_low - contra_low)
        results[dim_id] = {
            "nli_position": round(float(np.clip((margin + 2) / 4, 0.0, 1.0)), 3),
            "nli_confidence": round(float(np.clip(abs(margin) / 2, 0.0, 1.0)), 3),
            "relevance": round(r, 3)
        }
    return results

def split_sentences(text):
    if not text: return []
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p for p in parts if len(p) > 15]

def aggregate_sentence_scores(sentences, sentence_results, dim_id):
    contributors = []
    for sent, r in zip(sentences, sentence_results):
        entry = r[dim_id]
        if entry["nli_position"] is not None and entry["nli_confidence"] >= MIN_EVIDENCE_CONFIDENCE:
            contributors.append(entry)
    if not contributors:
        return {"nli_position": None, "nli_confidence": 0.0, "disagreement": None, "n_evidence": 0}
    total_w = sum(c["nli_confidence"] for c in contributors)
    weighted_pos = sum(c["nli_position"] * c["nli_confidence"] for c in contributors) / total_w
    positions = [c["nli_position"] for c in contributors]
    disagreement = round(max(positions) - min(positions), 3) if len(positions) > 1 else 0.0
    return {"nli_position": round(weighted_pos, 3), "nli_confidence": round(total_w/len(contributors), 3),
            "disagreement": disagreement, "n_evidence": len(contributors)}

def compute_prior(dim_id, company_values, crosswalk):
    num, den = 0.0, 0.0
    for v_id, tier in company_values.items():
        key = (v_id, dim_id)
        if key not in crosswalk: continue
        pos, loading = crosswalk[key]
        w = TIER_WEIGHTS.get(tier, 0.5) * loading
        num += w * pos; den += w
    return round(num / den, 3) if den > 0 else None

def subspace_similarity(vec_a, vec_b, full_dim_count=17):
    shared = [d for d in vec_a if vec_a.get(d) is not None and vec_b.get(d) is not None]
    if len(shared) < MIN_SHARED_DIMS: return None, None, len(shared)
    a = np.array([vec_a[d] for d in shared]) - 0.5
    b = np.array([vec_b[d] for d in shared]) - 0.5
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0: return None, None, len(shared)
    raw_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    weight = min(1.0, (len(shared) - MIN_SHARED_DIMS + 1) / (full_dim_count - MIN_SHARED_DIMS + 1))
    return round(raw_sim * weight, 4), round(raw_sim, 4), len(shared)

def main():
    print("Connecting to kiarsy_affinity database...", flush=True)
    conn = psycopg2.connect(dbname="kiarsy_affinity", user="yasso")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT dimension_id, low_anchor, high_anchor FROM dimensions WHERE dimension_type = 'values'")
    DIMENSIONS = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    FULL_DIM_COUNT = len(DIMENSIONS)

    cur.execute("SELECT value_id, dimension_id, position, loading FROM value_dimension_signatures")
    CROSSWALK = {(r[0], r[1]): (float(r[2]), float(r[3])) for r in cur.fetchall()}

    # --- Resume-aware run handling ---
    cur.execute("SELECT max(run_id) FROM scoring_runs")
    latest = cur.fetchone()[0]
    run_id = None
    if latest is not None:
        cur.execute("SELECT count(*) FROM company_symbol_affinity WHERE run_id = %s", (latest,))
        if cur.fetchone()[0] == 0:
            run_id = latest
            cur.execute("SELECT count(*) FROM symbol_dimension_scores WHERE run_id = %s", (run_id,))
            print(f"♻️  Resuming incomplete run #{run_id} ({cur.fetchone()[0]} symbol scores already saved)", flush=True)
    if run_id is None:
        cur.execute("INSERT INTO scoring_runs (model_name, embed_model) VALUES ('nli-deberta-v3', 'MiniLM-L6-v2') RETURNING run_id")
        run_id = cur.fetchone()[0]
        conn.commit()
        print(f"🆕 Started new scoring run #{run_id}", flush=True)

    # --- Symbols: commit per symbol, skip already-scored ---
    print("\n--- SCORING SYMBOLS ---", flush=True)
    cur.execute("SELECT symbol_id, documented_meaning FROM symbols")
    symbols = cur.fetchall()
    cur.execute("SELECT DISTINCT symbol_id FROM symbol_dimension_scores WHERE run_id = %s", (run_id,))
    done_syms = {r[0] for r in cur.fetchall()}

    for i, (sym_id, meaning) in enumerate(symbols, 1):
        if sym_id in done_syms:
            continue
        res = nli_score_all(meaning, DIMENSIONS)
        n_hit = 0
        for dim_id, data in res.items():
            if data["nli_position"] is not None:
                n_hit += 1
                cur.execute("""INSERT INTO symbol_dimension_scores 
                    (symbol_id, dimension_id, run_id, position, n_evidence, confidence)
                    VALUES (%s, %s, %s, %s, 1, %s)
                    ON CONFLICT DO NOTHING""",
                    (sym_id, dim_id, run_id, data["nli_position"], data["nli_confidence"]))
        conn.commit()
        gc.collect()
        print(f"  [{i}/{len(symbols)}] {sym_id}: {n_hit} dims scored", flush=True)
    print("✅ Symbol scoring phase complete.", flush=True)

    # --- Companies: commit per company, skip already-scored ---
    print("\n--- SCORING COMPANIES ---", flush=True)
    cur.execute("SELECT company_id, company_name, company_summary FROM companies")
    companies = cur.fetchall()
    cur.execute("SELECT DISTINCT company_id FROM company_dimension_scores WHERE run_id = %s", (run_id,))
    done_companies = {r[0] for r in cur.fetchall()}

    for c_id, c_name, c_summary in companies:
        if c_id in done_companies:
            print(f"⏭️  {c_name} already scored, skipping", flush=True)
            continue
        print(f"\nProcessing {c_name}...", flush=True)
        cur.execute("SELECT value_id, tier, evidence_summary FROM company_values WHERE company_id = %s", (c_id,))
        c_values_rows = cur.fetchall()
        c_values_dict = {r[0]: r[1] for r in c_values_rows}
        all_text = c_summary or ""
        for r in c_values_rows:
            if r[2]: all_text += " " + r[2]
        sentences = split_sentences(all_text)
        sentence_results = [nli_score_all(s, DIMENSIONS) for s in sentences]
        for dim_id in DIMENSIONS:
            agg = aggregate_sentence_scores(sentences, sentence_results, dim_id)
            prior_pos = compute_prior(dim_id, c_values_dict, CROSSWALK)
            nli_pos, nli_conf = agg["nli_position"], agg["nli_confidence"]
            if nli_pos is not None and prior_pos is not None:
                final = round(nli_conf * nli_pos + (1 - nli_conf) * prior_pos, 3)
                method = "blended"
            elif nli_pos is not None:
                final, method = nli_pos, "nli_only"
            elif prior_pos is not None:
                final, method = prior_pos, "prior_only"
            else:
                final, method = None, "unscored"
            if agg["disagreement"] is not None and agg["disagreement"] > DISAGREEMENT_CEILING:
                final = None
            if final is not None:
                cur.execute("""INSERT INTO company_dimension_scores 
                    (company_id, dimension_id, run_id, nli_position, nli_confidence, off_topic_flag, prior_position, final_position, n_evidence, disagreement, method)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING""",
                    (c_id, dim_id, run_id, nli_pos, nli_conf, nli_pos is None, prior_pos, final, agg.get("n_evidence", 0), agg["disagreement"], method))
        conn.commit()
        gc.collect()
        print(f"✅ {c_name} vector saved.", flush=True)

    # --- Affinity matches ---
    print("\n--- CALCULATING AFFINITY MATCHES ---", flush=True)
    cur.execute("DELETE FROM company_symbol_affinity WHERE run_id = %s", (run_id,))
    conn.commit()
    cur.execute("SELECT company_id, dimension_id, final_position FROM company_dimension_scores WHERE run_id = %s AND final_position IS NOT NULL", (run_id,))
    company_vectors = {}
    for r in cur.fetchall():
        company_vectors.setdefault(r[0], {})[r[1]] = float(r[2])
    cur.execute("SELECT symbol_id, dimension_id, position FROM symbol_dimension_scores WHERE run_id = %s", (run_id,))
    symbol_vectors = {}
    for r in cur.fetchall():
        symbol_vectors.setdefault(r[0], {})[r[1]] = float(r[2])
    cur.execute("SELECT symbol_id, culture_id FROM symbols")
    sym_cultures = {r[0]: r[1] for r in cur.fetchall()}

    for c_id, c_vec in company_vectors.items():
        matches = []
        for s_id, s_vec in symbol_vectors.items():
            adj_sim, raw_sim, shared = subspace_similarity(c_vec, s_vec, FULL_DIM_COUNT)
            if adj_sim is not None:
                matches.append((s_id, adj_sim, raw_sim, shared))
        matches.sort(key=lambda x: x[1], reverse=True)
        culture_counts = {}
        for s_id, adj_sim, raw_sim, shared in matches:
            cult = sym_cultures.get(s_id)
            culture_counts[cult] = culture_counts.get(cult, 0) + 1
            cur.execute("""INSERT INTO company_symbol_affinity 
                (company_id, symbol_id, run_id, similarity, raw_similarity, shared_dimensions, evidence_weight, rank_in_culture)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING""",
                (c_id, s_id, run_id, adj_sim, raw_sim, shared, round(adj_sim/raw_sim if raw_sim else 0, 3), culture_counts[cult]))
        conn.commit()
    print("\n🎉 Pipeline complete! Run the Top-10 query now.", flush=True)

if __name__ == "__main__":
    main()
