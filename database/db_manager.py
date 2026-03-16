import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'applications.db')


def init_db():
    """Initialize SQLite database with applications table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT    NOT NULL,
            job_title     TEXT,
            ats_score     REAL,
            missing_skills TEXT,
            steps_run     TEXT
        )
    ''')
    # Add job_title column if upgrading from older schema that used job_role
    try:
        cursor.execute('ALTER TABLE applications ADD COLUMN job_title TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def save_application(
    job_title: str = 'Unknown',
    ats_score: float = 0.0,
    missing_skills: str = '',
    steps_run: List[str] = None,
    resume_path: str = '',
    timestamp: str = None,
) -> None:
    """
    Save a completed analysis session to the database.

    Args:
        job_title:      Job title extracted from the job description.
        ats_score:      ATS compatibility score (0–100).
        missing_skills: Comma-separated list of missing skills.
        steps_run:      List of tool names that were executed.
        resume_path:    Path to the uploaded resume (not stored, just for logging).
        timestamp:      ISO timestamp string. Defaults to now.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''INSERT INTO applications
           (timestamp, job_title, ats_score, missing_skills, steps_run)
           VALUES (?, ?, ?, ?, ?)''',
        (
            timestamp or datetime.now().isoformat(),
            job_title,
            round(float(ats_score), 1),
            missing_skills if isinstance(missing_skills, str)
                else ', '.join(missing_skills),
            ', '.join(steps_run) if steps_run else '',
        )
    )
    conn.commit()
    conn.close()


def get_applications() -> List[Dict[str, Any]]:
    """Retrieve all saved applications, most recent first."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Support both old schema (job_role) and new schema (job_title)
    cursor.execute("PRAGMA table_info(applications)")
    columns = [row[1] for row in cursor.fetchall()]

    cursor.execute('SELECT * FROM applications ORDER BY timestamp DESC')
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        record = dict(zip(columns, row))
        # Normalise: always expose as job_title for the frontend
        if 'job_role' in record and 'job_title' not in record:
            record['job_title'] = record.pop('job_role')
        result.append(record)

    return result


# Initialize on import
init_db()