"""
Kiarsy API v2 — PostgreSQL only (for Angular)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os

app = FastAPI(title="Kiarsy API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "kiarsy_affinity"),
        user=os.getenv("DB_USER", "yasso"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


@app.get("/")
def root():
    return {"status": "online", "source": "postgresql"}


@app.get("/companies")
def list_companies():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT company_id, company_name, industry, country_region, websites
        FROM companies
        ORDER BY company_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"count": len(rows), "companies": rows}


@app.get("/companies/{company_id}")
def get_company(company_id: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT company_id, company_name, industry, country_region, websites, company_summary
        FROM companies WHERE company_id = %s
    """, (company_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(404, "Company not found")
    return row


@app.get("/companies/{company_id}/values")
def company_values(company_id: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT uv.value_name, cv.tier, cv.evidence_summary
        FROM company_values cv
        JOIN universal_values uv ON uv.value_id = cv.value_id
        WHERE cv.company_id = %s
        ORDER BY
          CASE cv.tier
            WHEN 'Explicit' THEN 1
            WHEN 'Strongly Supported' THEN 2
            ELSE 3
          END,
          uv.value_name
    """, (company_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"company_id": company_id, "values": rows}


@app.get("/companies/{company_id}/dimensions")
def company_dimensions(company_id: str):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT d.dimension_id, d.dimension_name, d.low_label, d.high_label,
               cds.final_position, cds.method, cds.n_evidence
        FROM company_dimension_scores cds
        JOIN dimensions d ON d.dimension_id = cds.dimension_id
        WHERE cds.company_id = %s
          AND cds.run_id = (SELECT max(run_id) FROM scoring_runs)
          AND cds.final_position IS NOT NULL
        ORDER BY d.sort_order, d.dimension_name
    """, (company_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"company_id": company_id, "dimensions": rows}


@app.get("/companies/{company_id}/matches")
def company_matches(company_id: str, open_only: bool = True, limit: int = 20):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    sql = """
        SELECT s.symbol_id, s.symbol_name, s.culture_id, s.documented_meaning,
               s.usage_status, s.usage_note,
               a.similarity, a.raw_similarity, a.shared_dimensions, a.rank_in_culture
        FROM company_symbol_affinity a
        JOIN symbols s ON s.symbol_id = a.symbol_id
        WHERE a.company_id = %s
          AND a.run_id = (SELECT max(run_id) FROM scoring_runs)
    """
    params = [company_id]
    if open_only:
        sql += " AND s.usage_status = 'open'"
    sql += " ORDER BY a.similarity DESC LIMIT %s"
    params.append(limit)

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"company_id": company_id, "count": len(rows), "matches": rows}


@app.get("/cultures")
def list_cultures():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT culture_id, culture_name FROM cultures ORDER BY culture_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"cultures": rows}


@app.post("/cultures")
def add_culture(payload: dict):
    culture_id = (payload.get("culture_id") or "").strip().lower().replace(" ", "_")
    culture_name = (payload.get("culture_name") or "").strip()
    if not culture_id or not culture_name:
        raise HTTPException(400, "culture_id and culture_name are required")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO cultures (culture_id, culture_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (culture_id, culture_name),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"ok": True, "culture_id": culture_id, "culture_name": culture_name}


@app.post("/symbols")
def add_symbol(payload: dict):
    required = ["symbol_id", "symbol_name", "culture_id", "documented_meaning"]
    for k in required:
        if not (payload.get(k) or "").strip():
            raise HTTPException(400, f"{k} is required")

    symbol_id = payload["symbol_id"].strip()
    symbol_name = payload["symbol_name"].strip()
    culture_id = payload["culture_id"].strip()
    meaning = payload["documented_meaning"].strip()
    sources = (payload.get("sources") or "").strip() or None
    source_url = (payload.get("source_url") or "").strip() or None
    verification_level = payload.get("verification_level") or "probable"
    usage_status = payload.get("usage_status") or "open"
    usage_note = (payload.get("usage_note") or "").strip() or None

    if verification_level not in ("verified", "verified_candidate", "probable_strong", "probable"):
        raise HTTPException(400, "invalid verification_level")
    if usage_status not in ("open", "restricted"):
        raise HTTPException(400, "invalid usage_status")

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM cultures WHERE culture_id = %s", (culture_id,))
        if not cur.fetchone():
            raise HTTPException(400, f"Unknown culture_id: {culture_id}. Create the culture first.")

        cur.execute(
            """
            INSERT INTO symbols (
              symbol_id, symbol_name, culture_id, documented_meaning,
              sources, source_url, verification_level, usage_status, usage_note
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (symbol_id) DO UPDATE SET
              symbol_name = EXCLUDED.symbol_name,
              documented_meaning = EXCLUDED.documented_meaning,
              sources = EXCLUDED.sources,
              source_url = EXCLUDED.source_url,
              verification_level = EXCLUDED.verification_level,
              usage_status = EXCLUDED.usage_status,
              usage_note = EXCLUDED.usage_note
            """,
            (
                symbol_id, symbol_name, culture_id, meaning,
                sources, source_url, verification_level, usage_status, usage_note,
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {
        "ok": True,
        "symbol_id": symbol_id,
        "note": "Symbol saved. Run the scorer to include it in matches: python scripts/scorer.py",
    }


@app.delete("/companies/{company_id}")
def delete_company(company_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM company_symbol_affinity WHERE company_id = %s", (company_id,))
        cur.execute("DELETE FROM company_dimension_scores WHERE company_id = %s", (company_id,))
        cur.execute("DELETE FROM company_values WHERE company_id = %s", (company_id,))
        cur.execute("DELETE FROM companies WHERE company_id = %s", (company_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Company not found")
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"ok": True, "deleted": company_id}


@app.delete("/symbols/{symbol_id}")
def delete_symbol(symbol_id: str):
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM company_symbol_affinity WHERE symbol_id = %s", (symbol_id,))
        cur.execute("DELETE FROM symbol_dimension_scores WHERE symbol_id = %s", (symbol_id,))
        cur.execute("DELETE FROM symbol_value_matches WHERE symbol_id = %s", (symbol_id,))
        cur.execute("DELETE FROM symbols WHERE symbol_id = %s", (symbol_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Symbol not found")
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"ok": True, "deleted": symbol_id}


@app.delete("/cultures/{culture_id}")
def delete_culture(culture_id: str):
    """Deletes culture only if it has no symbols left."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT count(*) FROM symbols WHERE culture_id = %s", (culture_id,))
        n = cur.fetchone()[0]
        if n > 0:
            raise HTTPException(
                400,
                f"Culture still has {n} symbols. Delete or move symbols first.",
            )
        cur.execute("DELETE FROM cultures WHERE culture_id = %s", (culture_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Culture not found")
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {"ok": True, "deleted": culture_id}


@app.get("/symbols")
def list_symbols(culture_id: str | None = None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if culture_id:
        cur.execute(
            """
            SELECT symbol_id, symbol_name, culture_id, usage_status, verification_level
            FROM symbols WHERE culture_id = %s
            ORDER BY symbol_name
            """,
            (culture_id,),
        )
    else:
        cur.execute(
            """
            SELECT symbol_id, symbol_name, culture_id, usage_status, verification_level
            FROM symbols
            ORDER BY culture_id, symbol_name
            """
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"count": len(rows), "symbols": rows}


@app.post("/companies/process")
def process_company(payload: dict):
    """
    Runs the full automatic pipeline in a subprocess:
    scrape → values → dimensions → symbol matches
    """
    import subprocess
    from pathlib import Path

    name = (payload.get("company_name") or "").strip()
    url = (payload.get("website_url") or "").strip()
    industry = (payload.get("industry") or "").strip()
    region = (payload.get("region") or "").strip()

    if not name or not url:
        raise HTTPException(400, "company_name and website_url are required")

    root = Path.home() / "kiarsy"
    script = root / "scripts" / "auto_pipeline.py"
    if not script.exists():
        raise HTTPException(500, "auto_pipeline.py not found")

    cmd = [
        str(root / "venv" / "bin" / "python"),
        str(script),
        name,
        url,
        industry,
        region,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=900,  # 15 minutes max
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(500, "Processing timed out")

    if result.returncode != 0:
        raise HTTPException(
            500,
            f"Pipeline failed:\n{result.stderr[-2000:] or result.stdout[-2000:]}",
        )

    return {
        "ok": True,
        "company_name": name,
        "log_tail": (result.stdout or "")[-2500:],
        "message": "Company processed. Refresh DNA / Matches pages.",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
