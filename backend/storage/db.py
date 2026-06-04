"""Compatibility storage functions backed by the PostgreSQL job repository."""

from __future__ import annotations

from repository.jobs import JobRepository

try:
    from config.settings import DEDUP_WINDOW_HOURS, DEFAULT_SEARCH_LIMIT, DEFAULT_SEARCH_OFFSET
except ModuleNotFoundError:
    DEDUP_WINDOW_HOURS = 24
    DEFAULT_SEARCH_LIMIT = 50
    DEFAULT_SEARCH_OFFSET = 0

_repository = JobRepository()


def init_db(db_path: str | None = None) -> None:
    """Create database tables if they do not exist."""
    _repository.init_schema()


def is_duplicate(fingerprint: str, db_path: str | None = None) -> bool:
    return _repository.is_duplicate(fingerprint, dedup_window_hours=DEDUP_WINDOW_HOURS)


def save_job(job: dict, source: str, db_path: str | None = None) -> tuple[bool, str]:
    return _repository.save_job(job, source, dedup_window_hours=DEDUP_WINDOW_HOURS)


def start_run(source: str, db_path: str | None = None) -> int:
    return _repository.start_run(source)


def finish_run(
    run_id: int,
    items_new: int,
    items_dupe: int,
    status: str = "completed",
    db_path: str | None = None,
) -> None:
    _repository.finish_run(run_id, items_new, items_dupe, status)


def recent_jobs(
    hours: int = 24,
    source: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    return _repository.recent_jobs(hours=hours, source=source)


def get_jobs_by_fingerprints(
    fingerprints: list[str],
    db_path: str | None = None,
) -> list[dict]:
    return _repository.get_jobs_by_fingerprints(fingerprints)


def search_jobs(
    keywords: list[str] | None = None,
    countries: list[str] | None = None,
    company: str | None = None,
    remote: bool | None = None,
    limit: int = DEFAULT_SEARCH_LIMIT,
    offset: int = DEFAULT_SEARCH_OFFSET,
    db_path: str | None = None,
) -> tuple[list[dict], int]:
    return _repository.search_jobs(
        keywords=keywords,
        countries=countries,
        company=company,
        remote=remote,
        limit=limit,
        offset=offset,
    )
