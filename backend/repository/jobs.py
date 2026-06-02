"""PostgreSQL repository for scraped jobs and scrape runs."""

from __future__ import annotations

import hashlib
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - handled at runtime when DB is used.
    psycopg = None
    dict_row = None

logger = logging.getLogger("job_aggregator.repository.jobs")


DEFAULT_DATABASE_URL = "postgresql://job_user:job_password@postgres:5432/job_automation"


class JobRepository:
    """Synchronous repository used by both FastAPI services and spider hooks."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

    @contextmanager
    def _connect(self) -> Iterator:
        if psycopg is None:
            raise RuntimeError("psycopg is not installed. Install psycopg[binary] to use PostgreSQL.")
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            yield conn

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id BIGSERIAL PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    company TEXT,
                    location TEXT,
                    url TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    salary TEXT,
                    source TEXT NOT NULL,
                    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );

                CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs (fingerprint);
                CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs (scraped_at);
                CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs (source);

                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id BIGSERIAL PRIMARY KEY,
                    source TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMPTZ,
                    items_new INTEGER DEFAULT 0,
                    items_dupe INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                );
                """
            )
        logger.info("PostgreSQL schema is ready.")

    def is_duplicate(self, fingerprint: str, dedup_window_hours: int = 24) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=dedup_window_hours)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM jobs WHERE fingerprint = %s AND scraped_at >= %s LIMIT 1",
                (fingerprint, cutoff),
            ).fetchone()
        return row is not None

    def save_job(
        self,
        job: dict,
        source: str,
        dedup_window_hours: int = 24,
    ) -> tuple[bool, str]:
        fingerprint = self.fingerprint(job)
        if self.is_duplicate(fingerprint, dedup_window_hours=dedup_window_hours):
            return False, fingerprint

        tags = job.get("tags", [])
        tags_value = ",".join(tags) if isinstance(tags, list) else str(tags or "")

        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO jobs
                    (fingerprint, title, company, location, url, description, tags, salary, source)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (fingerprint) DO NOTHING
                RETURNING id
                """,
                (
                    fingerprint,
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("url", ""),
                    job.get("description", ""),
                    tags_value,
                    job.get("salary", ""),
                    source,
                ),
            ).fetchone()
        return row is not None, fingerprint

    def start_run(self, source: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "INSERT INTO scrape_runs (source) VALUES (%s) RETURNING id",
                (source,),
            ).fetchone()
        return int(row["id"])

    def finish_run(
        self,
        run_id: int,
        items_new: int,
        items_dupe: int,
        status: str = "completed",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scrape_runs
                   SET finished_at = NOW(), items_new = %s, items_dupe = %s, status = %s
                 WHERE id = %s
                """,
                (items_new, items_dupe, status, run_id),
            )

    def recent_jobs(self, hours: int = 24, source: str | None = None) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        params: list[object] = [cutoff]
        query = "SELECT * FROM jobs WHERE scraped_at >= %s"
        if source:
            query += " AND source = %s"
            params.append(source)
        query += " ORDER BY scraped_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_jobs_by_fingerprints(self, fingerprints: list[str]) -> list[dict]:
        if not fingerprints:
            return []
        placeholders = ", ".join(["%s"] * len(fingerprints))
        query = f"SELECT * FROM jobs WHERE fingerprint IN ({placeholders})"
        with self._connect() as conn:
            rows = conn.execute(query, fingerprints).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def fingerprint(job: dict) -> str:
        raw = f"{job.get('url', '').strip().lower()}|{job.get('title', '').strip().lower()}"
        return hashlib.sha1(raw.encode()).hexdigest()
