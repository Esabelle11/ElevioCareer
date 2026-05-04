import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
import psycopg2
from psycopg2.extras import RealDictCursor
import random

_MODELS_SQL = Path(__file__).resolve().parent / "models.sql"


# -----------------------------
# CONNECTION
# -----------------------------
def get_conn():
    return psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=settings.DB_PORT
    )


# -----------------------------
# INIT DB (RUN ONCE AT STARTUP)
# -----------------------------
def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            with open(_MODELS_SQL, "r", encoding="utf-8") as f:
                cur.execute(f.read())
        conn.commit()

        


# -----------------------------
# JOB UPSERT
# -----------------------------
def upsert_job(job: dict, batch_seed: str | None = None) -> None:
    """Insert or update a job. All jobs in one scrape run share the same batch_seed."""
    seed = batch_seed if batch_seed is not None else str(random.randint(1, 1000000))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO jobs (job_url, title, company, location, description, source, section_random_seed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_url)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    company = EXCLUDED.company,
                    location = EXCLUDED.location,
                    description = EXCLUDED.description,
                    last_seen_at = CURRENT_TIMESTAMP,
                    section_random_seed = EXCLUDED.section_random_seed,
                    is_active = TRUE;
                """,
                (
                    job["job_url"],
                    job["title"],
                    job["company"],
                    job["location"],
                    job["description"],
                    job["source"],
                    seed,
                ),
            )
        conn.commit()

# -----------------------------
# GET JOBS BY SECTION RANDOM SEED
# -----------------------------
def get_jobs_by_section_random_seed(section_random_seed):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT title, company, description ,job_url,source FROM jobs WHERE section_random_seed = %s", (section_random_seed,))
            rows = cur.fetchall()
    return [{"title": r[0], "company": r[1], "description": r[2], "job_url": r[3], "source": r[4]} for r in rows]    

# -----------------------------
# LIMIT CHECK
# -----------------------------
MAX_ANALYSES_PER_DAY = 3

def check_user_limit(user_id: str) -> bool:
    """Return True if user has reached daily limit"""
    today = datetime.now(timezone.utc).date()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM resume_analysis
                WHERE user_id = %s
                AND DATE(created_at) = %s
            """, (user_id, today))

            row = cur.fetchone()
            return row[0] >= MAX_ANALYSES_PER_DAY


# -----------------------------
# INSERT ANALYSIS
# -----------------------------
def insert_analysis(
    user_id: str | None,
    resume_text: str,
    job_text: str,
    total_score: float,
    ai_output: dict,
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO resume_analysis
                (user_id, resume_text, job_text, total_score, ai_output_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                resume_text[:50000],
                job_text[:50000],
                total_score,
                json.dumps(ai_output),
                datetime.now(timezone.utc),
            ))

            new_id = cur.fetchone()[0]

        conn.commit()
        return new_id


# -----------------------------
# LIST HISTORY
# -----------------------------
def list_history(user_id: str | None, limit: int = 10) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            if user_id:
                cur.execute("""
                    SELECT id, user_id, total_score, ai_output_json, created_at
                    FROM resume_analysis
                    WHERE user_id = %s
                    ORDER BY id DESC
                    LIMIT %s
                """, (user_id, limit))
            else:
                cur.execute("""
                    SELECT id, user_id, total_score, ai_output_json, created_at
                    FROM resume_analysis
                    ORDER BY id DESC
                    LIMIT %s
                """, (limit,))

            rows = cur.fetchall()
            return list(rows)