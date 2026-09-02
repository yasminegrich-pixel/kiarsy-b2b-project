# KIARSY Scoring Spec v1
Notation: d=dimension; L,H=anchors; u=sentence unit; (c,e,n)=contra/entail/neutral;
t=tier weight; l=loading; p=crosswalk position; C=NLI confidence dial.

## Stage 1 — Sentence-level NLI
F1 p = softmax([c,e,n]) per (unit,anchor)
F2 lean_L = p_e(u,L)-p_c(u,L); lean_H = p_e(u,H)-p_c(u,H)
F3 margin m = lean_H - lean_L  (in [-2,2]; >0 leans high)

## Stage 2 — Gating
F4 rel(u,d) = max(cos(e(u),e(L)), cos(e(u),e(H))); keep if >= 0.30
F5 keep u iff |m| >= 0.20

## Stage 3 — Unit aggregation
F6 agg = sum(m*|m|)/sum(|m|); position = clip(agg/4+0.5, 0, 1)
   n_evidence = count; confidence = mean(|m|)
   No sentence passes F4 -> off-topic, position NULL.
   Passes F4 but none F5 -> balanced, position NULL. NULL = excluded, never 0.5.

## Stage 4 — Value Prior
F7 tiers: Explicit=1.0, Strongly Supported=0.7, Possible=0.4
F8 loadings: S=1.0, M=0.5
F9 prior_d = sum(t*l*p)/sum(t*l) over values loading on d; NULL if none
F10 prior_strength = sum(t*l)

## Stage 5 — Blend
F11 C = 0 if NLI NULL; 0.5 if n_evidence=1; 1 if n_evidence>=2
F12 final_d = C*NLI_d + (1-C)*prior_d; NULL only if both NULL

## Stage 6 — Matching
F13 D_shared = dims where both non-NULL; require |D_shared| >= 3
F14 sim = centered cosine (Pearson) over D_shared
F15 rank desc per culture, top 3; restricted symbols flagged

## Stage 7 — Validation
V1 measured vs judged crosswalk position; flag if |diff| > 0.2
V2 gold-set recovery: manual Core/Ready matches in top-3?
V3 sensitivity: positions +/-0.1, report top-3 overlap
V4 legacy rank correlation (old engine vs F14)

## Constants
RELEVANCE_FLOOR 0.30 (tunable) | MARGIN_FLOOR 0.20 (tunable) |
min shared dims 3 (frozen, DB constraint) | disagreement 0.2 (tunable) |
top-k 3 (business rule) | anchors FROZEN (edit = full re-score)

## DB map
F1-F6 -> scored_units, symbol_dimension_scores, company_dimension_scores
F7-F10 -> company_value_priors view
F11-F12 -> company_dimension_scores.final_position
F13-F15 -> company_symbol_affinity
