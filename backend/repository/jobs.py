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
from config.settings import DEFAULT_SEARCH_LIMIT, DEFAULT_SEARCH_OFFSET


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
        fingerprint = self.fingerprint(job, source)

        from services.filters import is_blacklisted_title
        if is_blacklisted_title(job.get("title")):
            logger.info("Dropping non-software job: %s", job.get("title"))
            return False, fingerprint

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

    def delete_old_jobs(
        self,
        days: int | None = None,
        hours: int | None = None,
        minutes: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        truncate: bool = False,
    ) -> list[dict]:
        """Deletes jobs based on relative age, date range, or truncates the table."""
        if truncate:
            query = "DELETE FROM jobs RETURNING *"
            params = ()
        elif start_date is not None or end_date is not None:
            clauses = []
            params_list = []
            if start_date is not None:
                clauses.append("scraped_at >= %s")
                params_list.append(start_date)
            if end_date is not None:
                clauses.append("scraped_at <= %s")
                params_list.append(end_date)
            query = f"DELETE FROM jobs WHERE {' AND '.join(clauses)} RETURNING *"
            params = tuple(params_list)
        else:
            # Default fallback to 2 days if no options are specified
            if days is None and hours is None and minutes is None:
                days = 2
            
            delta = timedelta(
                days=days or 0,
                hours=hours or 0,
                minutes=minutes or 0,
            )
            cutoff = datetime.now(timezone.utc) - delta
            query = "DELETE FROM jobs WHERE scraped_at < %s RETURNING *"
            params = (cutoff,)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def search_jobs(
        self,
        keywords: list[str] | None = None,
        countries: list[str] | None = None,
        company: str | None = None,
        remote: bool | None = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        offset: int = DEFAULT_SEARCH_OFFSET,
    ) -> tuple[list[dict], int]:
        where_clauses = []
        params = []
        
        if keywords:
            keyword_clauses = []
            for kw in keywords:
                if kw.strip():
                    keyword_clauses.append("(title ILIKE %s OR description ILIKE %s OR tags ILIKE %s)")
                    like_pattern = f"%{kw.strip()}%"
                    params.extend([like_pattern, like_pattern, like_pattern])
            if keyword_clauses:
                where_clauses.append("(" + " OR ".join(keyword_clauses) + ")")
        
        if countries:
            country_expansion = {
                "egypt": ["egypt", "cairo", "alexandria", "مصر", "\\_eg"],
                "eg": ["egypt", "cairo", "alexandria", "مصر", "\\_eg"],
                "saudi arabia": ["saudi", "riyadh", "jeddah", "السعودية", "\\_sa"],
                "saudi": ["saudi", "riyadh", "jeddah", "السعودية", "\\_sa"],
                "sa": ["saudi", "riyadh", "jeddah", "السعودية", "\\_sa"],
                "united arab emirates": ["uae", "dubai", "abu dhabi", "united arab emirates", "الامارات", "\\_ae", "emirates"],
                "uae": ["uae", "dubai", "abu dhabi", "united arab emirates", "الامارات", "\\_ae", "emirates"],
                "ae": ["uae", "dubai", "abu dhabi", "united arab emirates", "الامارات", "\\_ae", "emirates"],
                "emirates": ["uae", "dubai", "abu dhabi", "united arab emirates", "الامارات", "\\_ae", "emirates"],
                "emarties": ["uae", "dubai", "abu dhabi", "united arab emirates", "الامارات", "\\_ae", "emirates"],
                "germany": ["germany", "berlin", "munich", "frankfurt", "deutschland", "\\_germany"],
                "de": ["germany", "berlin", "munich", "frankfurt", "deutschland", "\\_germany"],
                "poland": ["poland", "warsaw", "krakow", "polska", "\\_poland"],
                "pl": ["poland", "warsaw", "krakow", "polska", "\\_poland"],
                "spain": ["spain", "barcelona", "madrid", "españa", "\\_spain", "\\_barcelona"],
                "es": ["spain", "barcelona", "madrid", "españa", "\\_spain", "\\_barcelona"],
                "canada": ["canada", "toronto", "vancouver", "montreal", "\\_canada"],
                "ca": ["canada", "toronto", "vancouver", "montreal", "\\_canada"],
                "united states": ["usa", "united states", "us", "new york", "san francisco", "california"],
                "usa": ["usa", "united states", "us", "new york", "san francisco", "california"],
                "us": ["usa", "united states", "us", "new york", "san francisco", "california"],
                "united kingdom": ["uk", "united kingdom", "london", "england"],
                "uk": ["uk", "united kingdom", "london", "england"],
            }
            country_clauses = []
            for c in countries:
                if c.strip():
                    c_key = c.lower().strip()
                    terms = country_expansion.get(c_key, [c.strip()])
                    for term in terms:
                        country_clauses.append("(location ILIKE %s OR tags ILIKE %s OR source ILIKE %s)")
                        like_pattern = f"%{term}%"
                        params.extend([like_pattern, like_pattern, like_pattern])
            if country_clauses:
                where_clauses.append("(" + " OR ".join(country_clauses) + ")")
            
        if company:
            where_clauses.append("company ILIKE %s")
            params.append(f"%{company}%")
            
        if remote is not None:
            if remote:
                where_clauses.append("(location ILIKE %s OR tags ILIKE %s OR title ILIKE %s)")
                params.extend(["%remote%", "%remote%", "%remote%"])
            else:
                where_clauses.append("(location NOT ILIKE %s AND tags NOT ILIKE %s AND title NOT ILIKE %s)")
                params.extend(["%remote%", "%remote%", "%remote%"])

        where_str = ""
        if where_clauses:
            where_str = " AND " + " AND ".join(where_clauses)

        # 1. Get total count
        count_query = f"SELECT COUNT(*) as count FROM jobs WHERE 1=1{where_str}"
        
        # 2. Get paginated results
        results_query = f"SELECT * FROM jobs WHERE 1=1{where_str} ORDER BY scraped_at DESC LIMIT %s OFFSET %s"
        results_params = params + [limit, offset]

        with self._connect() as conn:
            # We run count first
            count_row = conn.execute(count_query, params).fetchone()
            total_count = int(count_row["count"]) if count_row else 0
            
            rows = conn.execute(results_query, results_params).fetchall()
            jobs = [dict(row) for row in rows]
            
        return jobs, total_count

    @staticmethod
    def fingerprint(job: dict, source: str | None = None) -> str:
        # Generate fingerprint based on job title, company, and source to prevent duplicates in aggregation
        title = (job.get("title") or "").strip().lower()
        company = (job.get("company") or "").strip().lower()
        src = (source or job.get("source") or job.get("site") or "").strip().lower()
        raw = f"{title}|{company}|{src}"
        return hashlib.sha1(raw.encode()).hexdigest()
