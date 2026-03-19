"""
db_manager.py
-------------
Database layer for the Job Application Assistant.

- Uses PostgreSQL when DATABASE_URL is set in .env
- Falls back to SQLite automatically for local development
- Same public API as before: init_db(), save_application(), get_applications()
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "applications.db")

USE_POSTGRES = DATABASE_URL.startswith("postgresql")

# ---------------------------------------------------------------------------
# PostgreSQL helpers (only imported when needed)
# ---------------------------------------------------------------------------

def _pg_conn():
    """Return a psycopg2 connection using DATABASE_URL."""
    import psycopg2
    return psycopg2.connect(DATABASE_URL)


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create the applications table if it doesn't exist."""
    if USE_POSTGRES:
        _init_postgres()
    else:
        _init_sqlite()


def _init_postgres() -> None:
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id             SERIAL PRIMARY KEY,
                timestamp      TEXT    NOT NULL,
                job_title      TEXT,
                ats_score      REAL,
                missing_skills TEXT,
                steps_run      TEXT
            )
        """)
        conn.commit()
        cur.close()
        conn.close()
        logger.info("[DB] PostgreSQL table ready.")
    except Exception as e:
        logger.error(f"[DB] PostgreSQL init failed: {e}")
        raise


def _init_sqlite() -> None:
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT    NOT NULL,
            job_title      TEXT,
            ats_score      REAL,
            missing_skills TEXT,
            steps_run      TEXT
        )
    """)
    # Migrate old schema that used job_role instead of job_title
    try:
        cur.execute("ALTER TABLE applications ADD COLUMN job_title TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    # Migrate old schema missing steps_run
    try:
        cur.execute("ALTER TABLE applications ADD COLUMN steps_run TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    logger.info("[DB] SQLite table ready.")


# ---------------------------------------------------------------------------
# save_application
# ---------------------------------------------------------------------------

def save_application(
    job_title: str = "Unknown",
    ats_score: float = 0.0,
    missing_skills: str = "",
    steps_run: Optional[List[str]] = None,
    resume_path: str = "",   # kept for API compatibility, not stored
    timestamp: Optional[str] = None,
) -> None:
    """Persist one analysis session to the database."""
    ts = timestamp or datetime.now().isoformat()
    score = round(float(ats_score), 1)
    skills_str = (
        missing_skills
        if isinstance(missing_skills, str)
        else ", ".join(missing_skills)
    )
    steps_str = ", ".join(steps_run) if steps_run else ""

    if USE_POSTGRES:
        _save_postgres(ts, job_title, score, skills_str, steps_str)
    else:
        _save_sqlite(ts, job_title, score, skills_str, steps_str)


def _save_postgres(ts, job_title, ats_score, missing_skills, steps_run) -> None:
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO applications (timestamp, job_title, ats_score, missing_skills, steps_run)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (ts, job_title, ats_score, missing_skills, steps_run),
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"[DB] Saved to PostgreSQL: {job_title} | ATS {ats_score}%")
    except Exception as e:
        logger.error(f"[DB] PostgreSQL save failed: {e}")


def _save_sqlite(ts, job_title, ats_score, missing_skills, steps_run) -> None:
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO applications (timestamp, job_title, ats_score, missing_skills, steps_run)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ts, job_title, ats_score, missing_skills, steps_run),
        )
        conn.commit()
        conn.close()
        logger.info(f"[DB] Saved to SQLite: {job_title} | ATS {ats_score}%")
    except Exception as e:
        logger.error(f"[DB] SQLite save failed: {e}")


# ---------------------------------------------------------------------------
# get_applications
# ---------------------------------------------------------------------------

def get_applications() -> List[Dict[str, Any]]:
    """Return all saved analyses, most recent first."""
    if USE_POSTGRES:
        return _get_postgres()
    return _get_sqlite()


def _get_postgres() -> List[Dict[str, Any]]:
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, timestamp, job_title, ats_score, missing_skills, steps_run "
            "FROM applications ORDER BY timestamp DESC"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "job_title": r[2],
                "ats_score": r[3],
                "missing_skills": r[4],
                "steps_run": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[DB] PostgreSQL fetch failed: {e}")
        return []


def _get_sqlite() -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(SQLITE_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(applications)")
        columns = [row[1] for row in cur.fetchall()]
        cur.execute("SELECT * FROM applications ORDER BY timestamp DESC")
        rows = cur.fetchall()
        conn.close()
        result = []
        for row in rows:
            record = dict(zip(columns, row))
            # Normalise legacy job_role column
            if "job_role" in record and "job_title" not in record:
                record["job_title"] = record.pop("job_role")
            result.append(record)
        return result
    except Exception as e:
        logger.error(f"[DB] SQLite fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Run on import
# ---------------------------------------------------------------------------

init_db()