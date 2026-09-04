# KIARSY Scoring Spec v2 (Teammate Pipeline Integration)

## Stage 0: Models
- NLI: `cross-encoder/nli-deberta-v3-base` (Direction)
- Embeddings: `all-MiniLM-L6-v2` (Relevance)

## Stage 1: Relevance Gate (Embeddings)
F1 rel(u,d) = max(cos(u, L), cos(u, H))
F2 on_topic = (rel >= 0.20) AND (rel >= weakest_dim + 0.05)
   (If false -> NLI is skipped, position = NULL)

## Stage 2: Direction Scoring (NLI)
F3 lean_L = entail_L - contra_L; lean_H = entail_H - contra_H
F4 margin = lean_H - lean_L  (in [-2, 2])
F5 position = clip((margin + 2) / 4, 0, 1)
F6 confidence = clip(abs(margin) / 2, 0, 1)

## Stage 3: Sentence Aggregation (Company Passages)
F7 Filter: keep sentence iff confidence >= 0.10
F8 weighted_pos = sum(pos * conf) / sum(conf)
F9 disagreement = max(positions) - min(positions)

## Stage 4: Value Prior (from DB crosswalk)
F10 prior_d = sum(tier_w * loading * position) / sum(tier_w * loading)

## Stage 5: Blend
F11 final_d = (conf * nli_pos) + ((1 - conf) * prior_d)
   (Tracks 'method': blended, nli_only, prior_only, unscored)

## Stage 4.5: Disagreement Filter
F12 If disagreement > 0.50 -> final_d = NULL (Drop the dimension)

## Stage 6: Sub-space Similarity
F13 shared_dims = intersection of non-NULL dims (Require >= 3)
F14 Center vectors: v = v - 0.5
F15 raw_sim = cosine(v_company, v_symbol)
F16 evidence_weight = (shared - 3 + 1) / (17 - 3 + 1)
F17 adjusted_sim = raw_sim * evidence_weight
