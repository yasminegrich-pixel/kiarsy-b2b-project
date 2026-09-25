"""One-time script: create a Kiarsy admin user with hashed password."""
import os
import getpass
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from passlib.context import CryptContext

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "kiarsy_affinity"),
        user=os.getenv("DB_USER", "yasso"),
        password=os.getenv("DB_PASSWORD") or None,
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )


def main():
    print("Create Kiarsy admin user")
    username = input("Username: ").strip()
    email = input("Email (optional): ").strip() or None
    full_name = input("Full name (optional): ").strip() or None
    password = getpass.getpass("Password: ")
    password2 = getpass.getpass("Confirm password: ")

    if not username or not password:
        print("Username and password are required.")
        return
    if password != password2:
        print("Passwords do not match.")
        return
    if len(password) < 8:
        print("Use at least 8 characters.")
        return

    password_hash = pwd_context.hash(password)

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, 'admin', true)
            ON CONFLICT (username) DO UPDATE SET
              password_hash = EXCLUDED.password_hash,
              email = COALESCE(EXCLUDED.email, users.email),
              full_name = COALESCE(EXCLUDED.full_name, users.full_name),
              role = 'admin',
              is_active = true
            RETURNING user_id, username, role
            """,
            (username, email, password_hash, full_name),
        )
        row = cur.fetchone()
        conn.commit()
        print(f"OK — user_id={row[0]} username={row[1]} role={row[2]}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
