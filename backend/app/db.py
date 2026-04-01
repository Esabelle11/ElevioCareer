import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings


def get_conn() -> sqlite3.Connection:
    path = Path(settings.database_path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                resume_text TEXT,
                job_text TEXT,
                total_score REAL,
                ai_output_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()



MAX_ANALYSES_PER_DAY = 3
def check_user_limit(user_id: str) -> bool:
    """Return True if user has reached daily limit"""
    today = datetime.now(timezone.utc).date()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) FROM resume_analysis
            WHERE user_id = ? AND DATE(created_at) = ?
            """,
            (user_id, today)
        ).fetchone()
        if row and row[0] >= MAX_ANALYSES_PER_DAY:
            return True
    return False


def insert_analysis(
    user_id: str | None,
    resume_text: str,
    job_text: str,
    total_score: float,
    ai_output: dict,
) -> int:
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO resume_analysis
            (user_id, resume_text, job_text, total_score, ai_output_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                resume_text[:50000],
                job_text[:50000],
                total_score,
                json.dumps(ai_output),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def list_history(user_id: str | None, limit: int = 10) -> list[dict]:
    init_db()
    with get_conn() as conn:
        if user_id:
            rows = conn.execute(
                """
                SELECT id, user_id, total_score, ai_output_json, created_at
                FROM resume_analysis
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, user_id, total_score, ai_output_json, created_at
                FROM resume_analysis
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
