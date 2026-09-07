#!/usr/bin/env python3
"""Client Readiness Report — triages top company-symbol matches for human review.
Lightweight: reads Postgres only. No AI models loaded."""
import psycopg2, psycopg2.extras
from datetime import date
from pathlib import Path
from collections import OrderedDict

TOP_K_PER_CULTURE = 3
READY_THRESHOLD   = 0.15
REPORT_DIR        = Path.home() / "kiarsy" / "reports"

SERIOUS_KEYWORDS = ["slavery","captivity","sacred","funerary","funeral",
    "reserved for","legal","eagle feather","katsina","kachina",
    "do not use","do not reproduce","religious"]

ICON  = {"READY":"✅","REVIEW":"🔍","NOFIT":"❌","BLOCKED":"🚫"}
LABEL = {"READY":"CLIENT-READY","REVIEW":"REVIEW REQUIRED",
         "NOFIT":"NO FIT - do not force","BLOCKED":"BLOCKED - expert sign-off needed"}

def classify(status, sim, note):
    note = (note or "").lower()
    if status == "restricted":                 return "BLOCKED"
    if sim is None or sim <= 0:                return "NOFIT"
    if any(k in note for k in SERIOUS_KEYWORDS): return "REVIEW"
    if sim < READY_THRESHOLD:                  return "REVIEW"
    return "READY"

def main():
    conn = psycopg2.connect(dbname="kiarsy_affinity", user="yasso")
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT max(run_id) FROM scoring_runs"); run_id = cur.fetchone()[0]
    if run_id is None:
        print("No scoring runs found. Run scripts/scorer.py first."); return
    print(f"Using scoring run #{run_id}\n")

    cur.execute("""
        SELECT c.company_name, cul.culture_name,
               s.symbol_id, s.symbol_name, s.documented_meaning,
               s.usage_status, s.usage_note, s.verification_level,
               a.similarity, a.shared_dimensions, a.rank_in_culture
        FROM company_symbol_affinity a
        JOIN companies c  ON c.company_id = a.company_id
        JOIN symbols s    ON s.symbol_id  = a.symbol_id
        JOIN cultures cul ON cul.culture_id = s.culture_id
        WHERE a.run_id = %s AND a.rank_in_culture <= %s
        ORDER BY c.company_name, cul.culture_id, a.rank_in_culture
    """, (run_id, TOP_K_PER_CULTURE))
    rows = cur.fetchall()

    companies = OrderedDict()
    counts = {"READY":0,"REVIEW":0,"NOFIT":0,"BLOCKED":0}
    gaps = []
    for r in rows:
        companies.setdefault(r["company_name"], OrderedDict()) \
                 .setdefault(r["culture_name"], []).append(dict(r))

    md = [f"# Kiarsy Client-Readiness Report",
          f"_Run #{run_id} · {date.today().isoformat()} · top {TOP_K_PER_CULTURE}/culture · ready threshold {READY_THRESHOLD}_\n"]

    for cname, cults in companies.items():
        print("="*72); print(f"  {cname}"); print("="*72)
        md.append(f"\n## {cname}\n")
        for cult, matches in cults.items():
            print(f"\n  ▸ {cult}")
            md.append(f"\n### {cult}\n")
            best = max(float(m["similarity"]) for m in matches)
            for m in matches:
                sim = float(m["similarity"])
                v = classify(m["usage_status"], sim, m["usage_note"])
                counts[v] += 1
                head = f"    #{m['rank_in_culture']}  {m['symbol_name']}  [{m['symbol_id']}]  {ICON[v]} {LABEL[v]}  sim={sim:.3f}  dims={m['shared_dimensions']}"
                print(head)
                print(f"        Meaning: {m['documented_meaning']}")
                if m["usage_note"]:
                    print(f"        Note:    {m['usage_note']}")
                md.append(f"- **#{m['rank_in_culture']} {m['symbol_name']}** `[{m['symbol_id']}]` — {ICON[v]} **{LABEL[v]}** · sim `{sim:.3f}` · `{m['shared_dimensions']}` dims")
                md.append(f"  - Meaning: {m['documented_meaning']}")
                if m["usage_note"]:
                    md.append(f"  - Note: {m['usage_note']}")
            if best <= 0:
                gaps.append((cname, cult))
                print(f"    ⚠️  LIBRARY GAP: no positive {cult} match for this company.")

    print("\n" + "="*72); print("  SUMMARY"); print("="*72)
    for k in ["READY","REVIEW","NOFIT","BLOCKED"]:
        print(f"  {ICON[k]} {LABEL[k]:<32} {counts[k]}")
    if gaps:
        print("\n  GAPS to source new symbols for:")
        for cname, cult in gaps:
            print(f"    • {cname} — {cult}")

    md.append("\n## Summary\n")
    for k in ["READY","REVIEW","NOFIT","BLOCKED"]:
        md.append(f"- {ICON[k]} {LABEL[k]}: **{counts[k]}**")
    if gaps:
        md.append("\n### Library gaps (no positive match)\n")
        for cname, cult in gaps:
            md.append(f"- {cname} — {cult}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"client_readiness_run{run_id}_{date.today().isoformat()}.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"\n📄 Markdown report saved to: {out}")

    conn.close()

if __name__ == "__main__":
    main()
