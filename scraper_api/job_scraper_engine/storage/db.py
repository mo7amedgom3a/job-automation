"""
SQLite-backed storage layer.

Responsibilities:
  - Persist scraped job listings.
  - Deduplicate within a rolling time window.
  - Expose a simple API consumed by spiders and the scheduler.
"""

import hashlib
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

from config.settings import SQLITE_DB_PATH, DEDUP_WINDOW_HOURS

logger = logging.getLogger("job_scraper.storage")

# ─── Schema ──────────────────────────────────────────────────────────────────
_DDL = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    fingerprint   TEXT    NOT NULL UNIQUE,
    title         TEXT    NOT NULL,
    company       TEXT,
    location      TEXT,
    url           TEXT    NOT NULL,
    description   TEXT,
    tags          TEXT,           -- comma-separated
    salary        TEXT,
    source        TEXT    NOT NULL,
    scraped_at    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs (fingerprint);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at  ON jobs (scraped_at);
CREATE INDEX IF NOT EXISTS idx_jobs_source      ON jobs (source);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    items_new   INTEGER DEFAULT 0,
    items_dupe  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'running'   -- running | completed | failed
);
"""


@contextmanager
def _conn(db_path: str = SQLITE_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = SQLITE_DB_PATH) -> None:
    """Create tables if they don't exist yet."""
    with _conn(db_path) as conn:
        conn.executescript(_DDL)
    logger.info("Database initialised at %s", db_path)


# ─── Fingerprinting ──────────────────────────────────────────────────────────

def _fingerprint(job: dict) -> str:
    """
    Stable content-hash so the same job re-scraped later is detected as a dupe.
    Based on URL + title (lowercased) — not the auto-increment id.
    """
    raw = f"{job.get('url', '').strip().lower()}|{job.get('title', '').strip().lower()}"
    return hashlib.sha1(raw.encode()).hexdigest()


# ─── Public API ──────────────────────────────────────────────────────────────

def is_duplicate(fingerprint: str, db_path: str = SQLITE_DB_PATH) -> bool:
    """Return True if this fingerprint was seen within DEDUP_WINDOW_HOURS."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=DEDUP_WINDOW_HOURS)
    ).isoformat()
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE fingerprint = ? AND scraped_at >= ? LIMIT 1",
            (fingerprint, cutoff),
        ).fetchone()
    return row is not None


def save_job(job: dict, source: str, db_path: str = SQLITE_DB_PATH) -> tuple[bool, str]:
    """
    Persist a job dict.  Returns (was_new, fingerprint).
    Silently skips duplicates.
    """
    fp = _fingerprint(job)
    if is_duplicate(fp, db_path):
        return False, fp

    now = datetime.now(timezone.utc).isoformat()
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO jobs
                (fingerprint, title, company, location, url, description,
                 tags, salary, source, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fp,
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("url", ""),
                job.get("description", ""),
                ",".join(job.get("tags", [])) if isinstance(job.get("tags"), list) else job.get("tags", ""),
                job.get("salary", ""),
                source,
                now,
            ),
        )
    return True, fp


def start_run(source: str, db_path: str = SQLITE_DB_PATH) -> int:
    """Record a new scrape run; return its run_id."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO scrape_runs (source, started_at) VALUES (?, ?)",
            (source, now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def finish_run(
    run_id: int,
    items_new: int,
    items_dupe: int,
    status: str = "completed",
    db_path: str = SQLITE_DB_PATH,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn(db_path) as conn:
        conn.execute(
            """
            UPDATE scrape_runs
               SET finished_at = ?, items_new = ?, items_dupe = ?, status = ?
             WHERE id = ?
            """,
            (now, items_new, items_dupe, status, run_id),
        )


def recent_jobs(
    hours: int = 24,
    source: str | None = None,
    db_path: str = SQLITE_DB_PATH,
) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with _conn(db_path) as conn:
        query = "SELECT * FROM jobs WHERE scraped_at >= ?"
        params: list = [cutoff]
        if source:
            query += " AND source = ?"
            params.append(source)
        query += " ORDER BY scraped_at DESC"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]
