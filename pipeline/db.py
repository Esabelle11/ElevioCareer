import psycopg2
import os
from config import settings



def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=settings.DB_PORT
    )

def upsert_job(conn, job):
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO jobs (job_url, title, company, location, description, source)
        VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT (job_url)
        DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            location = EXCLUDED.location,
            description = EXCLUDED.description,
            last_seen_at = CURRENT_TIMESTAMP,
            is_active = TRUE;
        """, (
            job["job_url"],
            job["title"],
            job["company"],
            job["location"],
            job["description"],
            job["source"]
        ))
    conn.commit()