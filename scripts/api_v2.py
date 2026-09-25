"""
Kiarsy API v2 — PostgreSQL only (for Angular)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

import secrets
import string
import smtplib
from email.message import EmailMessage

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None


class UserCreateRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


def create_access_token(data: dict, expires_minutes: int = JWT_EXPIRE_MINUTES) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "role": role}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def require_editor_or_admin(user=Depends(get_current_user)):
    if user.get("role") not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Editor or admin role required")
    return user


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
        password=os.getenv("DB_PASSWORD") or None,
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


def _generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _send_reset_email(to_email: str, username: str, temp_password: str) -> None:
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    mail_from = os.getenv("SMTP_FROM", user)

    if not host or not user or not password:
        raise RuntimeError("SMTP is not configured")

    msg = EmailMessage()
    msg["Subject"] = "Kiarsy — temporary password"
    msg["From"] = mail_from
    msg["To"] = to_email
    msg.set_content(
        f"""Hello {username},

A password reset was requested for your Kiarsy account.

Temporary password: {temp_password}

1) Log in with this temporary password
2) Ask an admin to help you set a new permanent password if needed

If you did not request this, contact your Kiarsy administrator.

— Kiarsy
"""
    )

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)




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
def add_culture(payload: dict, user=Depends(require_editor_or_admin)):
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
def add_symbol(payload: dict, user=Depends(require_editor_or_admin)):
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
def delete_company(company_id: str, user=Depends(require_editor_or_admin)):
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
def delete_symbol(symbol_id: str, user=Depends(require_editor_or_admin)):
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
def delete_culture(culture_id: str, user=Depends(require_editor_or_admin)):
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


@app.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT username, password_hash, role, is_active
            FROM users
            WHERE username = %s
            """,
            (body.username.strip(),),
        )
        user = cur.fetchone()
        if not user or not user["is_active"]:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        if not pwd_context.verify(body.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        cur.execute(
            "UPDATE users SET last_login_at = now() WHERE username = %s",
            (user["username"],),
        )
        conn.commit()

        token = create_access_token(
            {"sub": user["username"], "role": user["role"]}
        )
        return TokenResponse(
            access_token=token,
            role=user["role"],
            username=user["username"],
        )
    finally:
        cur.close()
        conn.close()


@app.get("/auth/me")
def auth_me(user=Depends(get_current_user)):
    return user

@app.post("/auth/forgot-password")
def forgot_password(payload: dict):
    """
    Always returns a generic message (do not reveal whether the user exists).
    If the user exists and has an email, generate a temp password and email it.
    """
    username = (payload.get("username") or "").strip()
    generic = {
        "ok": True,
        "message": "If this account exists and has an email on file, a temporary password has been sent.",
    }
    if not username:
        return generic

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT user_id, username, email, is_active
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        user = cur.fetchone()
        if not user or not user["is_active"]:
            return generic

        if not user.get("email"):
            print(f"[RESET] user={username} has no email on file")
            return generic

        temp_password = _generate_temp_password()
        password_hash = pwd_context.hash(temp_password)

        cur.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (password_hash, user["user_id"]),
        )
        conn.commit()

        try:
            _send_reset_email(user["email"], user["username"], temp_password)
            print(f"[RESET] email sent to {user['email']} for user={username}")
        except Exception as e:
            # Keep the new password in DB, but log failure for admin
            print(f"[RESET] email FAILED for user={username}: {e}")
            print(f"[RESET] temporary_password={temp_password}")
            return {
                "ok": True,
                "message": "Password was reset, but email sending failed. Contact an administrator.",
            }

        return generic
    finally:
        cur.close()
        conn.close()

@app.get("/auth/profile")
def get_profile(user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT user_id, username, email, full_name, role, is_active, created_at, last_login_at
            FROM users
            WHERE username = %s
            """,
            (user["username"],),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        return row
    finally:
        cur.close()
        conn.close()


@app.put("/auth/profile")
def update_profile(body: ProfileUpdateRequest, user=Depends(get_current_user)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, username FROM users WHERE username = %s",
            (user["username"],),
        )
        me = cur.fetchone()
        if not me:
            raise HTTPException(404, "User not found")

        new_username = (body.username or me["username"]).strip()
        new_email = (body.email or "").strip() or None
        new_full_name = (body.full_name or "").strip() or None

        if not new_username:
            raise HTTPException(400, "Username cannot be empty")

        # username uniqueness
        cur.execute(
            "SELECT 1 FROM users WHERE username = %s AND user_id <> %s",
            (new_username, me["user_id"]),
        )
        if cur.fetchone():
            raise HTTPException(400, "Username already taken")

        cur.execute(
            """
            UPDATE users
            SET username = %s,
                email = %s,
                full_name = %s
            WHERE user_id = %s
            RETURNING user_id, username, email, full_name, role
            """,
            (new_username, new_email, new_full_name, me["user_id"]),
        )
        updated = cur.fetchone()
        conn.commit()

        # If username changed, issue a fresh token
        token = create_access_token(
            {"sub": updated["username"], "role": updated["role"]}
        )
        return {
            "user": updated,
            "access_token": token,
            "message": "Profile updated",
        }
    finally:
        cur.close()
        conn.close()


@app.post("/auth/change-password")
def change_password(body: PasswordChangeRequest, user=Depends(get_current_user)):
    if len(body.new_password or "") < 8:
        raise HTTPException(400, "New password must be at least 8 characters")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, password_hash FROM users WHERE username = %s",
            (user["username"],),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "User not found")

        if not pwd_context.verify(body.current_password, row["password_hash"]):
            raise HTTPException(400, "Current password is incorrect")

        cur.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (pwd_context.hash(body.new_password), row["user_id"]),
        )
        conn.commit()
        return {"ok": True, "message": "Password changed successfully"}
    finally:
        cur.close()
        conn.close()


@app.post("/companies/process")
def process_company(payload: dict, user=Depends(require_editor_or_admin)):
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


@app.get("/users")
def list_users(user=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            SELECT user_id, username, email, full_name, role, is_active,
                   created_at, last_login_at
            FROM users
            ORDER BY username
            """
        )
        return {"users": cur.fetchall()}
    finally:
        cur.close()
        conn.close()


@app.post("/users")
def create_user(body: UserCreateRequest, user=Depends(require_admin)):
    username = body.username.strip()
    role = (body.role or "viewer").strip()
    if role not in ("admin", "editor", "viewer"):
        raise HTTPException(400, "role must be admin, editor, or viewer")
    if len(body.password or "") < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if not username:
        raise HTTPException(400, "Username required")

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, %s, true)
            RETURNING user_id, username, email, full_name, role, is_active
            """,
            (
                username,
                (body.email or "").strip() or None,
                pwd_context.hash(body.password),
                (body.full_name or "").strip() or None,
                role,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        return {"ok": True, "user": row}
    except Exception as e:
        conn.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(400, "Username or email already exists")
        raise
    finally:
        cur.close()
        conn.close()


@app.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdateRequest, user=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(404, "User not found")

        if body.role is not None and body.role not in ("admin", "editor", "viewer"):
            raise HTTPException(400, "Invalid role")
        if body.password is not None and len(body.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters")

        fields = []
        values = []
        if body.email is not None:
            fields.append("email = %s")
            values.append(body.email.strip() or None)
        if body.full_name is not None:
            fields.append("full_name = %s")
            values.append(body.full_name.strip() or None)
        if body.role is not None:
            fields.append("role = %s")
            values.append(body.role)
        if body.is_active is not None:
            fields.append("is_active = %s")
            values.append(body.is_active)
        if body.password is not None:
            fields.append("password_hash = %s")
            values.append(pwd_context.hash(body.password))

        if not fields:
            raise HTTPException(400, "No changes provided")

        values.append(user_id)
        cur.execute(
            f"""
            UPDATE users SET {', '.join(fields)}
            WHERE user_id = %s
            RETURNING user_id, username, email, full_name, role, is_active
            """,
            values,
        )
        row = cur.fetchone()
        conn.commit()
        return {"ok": True, "user": row}
    finally:
        cur.close()
        conn.close()

@app.delete("/users/{user_id}")
def delete_user(user_id: int, user=Depends(require_admin)):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(
            "SELECT user_id, username FROM users WHERE user_id = %s",
            (user_id,),
        )
        target = cur.fetchone()
        if not target:
            raise HTTPException(404, "User not found")

        # Prevent deleting yourself
        if target["username"] == user.get("username"):
            raise HTTPException(400, "You cannot delete your own account")

        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        return {"ok": True, "deleted": target["username"]}
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
