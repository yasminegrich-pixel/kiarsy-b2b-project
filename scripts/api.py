#!/usr/bin/env python3
"""KIARSY B2B Design Engine — REST API"""
from fastapi import FastAPI, HTTPException
from pathlib import Path
from collections import defaultdict
import yaml

DATA_DIR = Path.home() / "kiarsy" / "data"

app = FastAPI(
    title="KIARSY B2B Design Engine API",
    description="Cultural symbol recommendation engine for B2B clients",
    version="1.0.0",
)

# ---------- Helpers ----------
def load_yaml(fp):
    with open(fp) as f:
        return yaml.safe_load(f)

def load_symbols():
    return [d for f in (DATA_DIR / "cultures").rglob("*.yaml")
            if (d := load_yaml(f))]

def load_companies():
    return [d for f in sorted((DATA_DIR / "companies").glob("*.yaml"))
            if (d := load_yaml(f))]

def merged_profile(company):
    merged = {}
    for val, w in company.get("channel_1", {}).get("values", {}).items():
        merged[val] = merged.get(val, 0) + w
    test_file = DATA_DIR / "tests" / f"{company['id']}_test.yaml"
    if test_file.exists():
        t = load_yaml(test_file) or {}
        for val, w in t.get("channel_2", {}).get("values", {}).items():
            merged[val] = merged.get(val, 0) + w
    return merged

def score_symbols(merged, symbols):
    by_culture = defaultdict(list)
    for sym in symbols:
        score = sum(merged.get(v, 0) for v in sym.get("values", []))
        matched = [v for v in sym.get("values", []) if v in merged]
        by_culture[sym.get("culture", "unknown")].append(
            {**sym, "match_score": score, "matched_values": matched})
    for c in by_culture:
        by_culture[c].sort(key=lambda x: x["match_score"], reverse=True)
    return by_culture

# ---------- Endpoints ----------
@app.get("/")
def root():
    return {"name": "KIARSY B2B Design Engine", "status": "online",
            "endpoints": ["/values", "/cultures", "/symbols", "/companies",
                          "/companies/{id}/profile", "/companies/{id}/recommendations"]}

@app.get("/values")
def get_values():
    return {"count": 15, "values": load_yaml(DATA_DIR / "values.yaml")["values"]}

@app.get("/cultures")
def get_cultures():
    counts = defaultdict(int)
    for s in load_symbols():
        counts[s.get("culture", "unknown")] += 1
    return {"count": len(counts), "cultures": dict(counts)}

@app.get("/symbols")
def get_symbols(culture: str = None, usage: str = None):
    symbols = load_symbols()
    if culture:
        symbols = [s for s in symbols if s.get("culture") == culture]
    if usage:
        symbols = [s for s in symbols if s.get("usage", "open") == usage]
    return {"count": len(symbols), "symbols": symbols}

@app.get("/symbols/{symbol_id}")
def get_symbol(symbol_id: str):
    for s in load_symbols():
        if s.get("id") == symbol_id:
            return s
    raise HTTPException(404, f"Symbol '{symbol_id}' not found")

@app.get("/companies")
def get_companies():
    companies = load_companies()
    return {"count": len(companies),
            "companies": [{"id": c["id"], "name": c["name"]} for c in companies]}

@app.get("/companies/{company_id}")
def get_company(company_id: str):
    for c in load_companies():
        if c.get("id") == company_id:
            return c
    raise HTTPException(404, f"Company '{company_id}' not found")

@app.get("/companies/{company_id}/profile")
def get_profile(company_id: str):
    company = get_company(company_id)
    merged = merged_profile(company)
    ranked = [{"value": v, "points": p}
              for v, p in sorted(merged.items(), key=lambda x: x[1], reverse=True)]
    return {"company": company["name"], "value_profile": ranked}

@app.get("/companies/{company_id}/recommendations")
def get_recommendations(company_id: str, per_culture: int = 3):
    company = get_company(company_id)
    merged = merged_profile(company)
    by_culture = score_symbols(merged, load_symbols())
    return {
        "company": company["name"],
        "value_profile": [{"value": v, "points": p}
                          for v, p in sorted(merged.items(), key=lambda x: x[1], reverse=True)],
        "recommendations": {c: syms[:per_culture] for c, syms in by_culture.items()},
    }
