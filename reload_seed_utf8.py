import psycopg2
import os

conn = psycopg2.connect(
    dbname="kiarsy_affinity",
    user="yasso",
    password=os.environ.get("PGPASSWORD"),
    host="localhost",
    client_encoding="UTF8",
)
conn.autocommit = True
cur = conn.cursor()

with open("db/seed.sql", "r", encoding="utf-8") as f:
    sql = f.read()

cur.execute(sql)
print("Seed data loaded successfully with UTF-8 encoding.")

cur.close()
conn.close()