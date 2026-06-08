"""Job management endpoints."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query, HTTPException
from datetime import datetime

from dependencies import get_job_repository
from models.job import DeleteOldJobsResponse, JobItem
from repository.jobs import JobRepository

logger = logging.getLogger("job_aggregator.routes.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.delete(
    "/old",
    response_model=DeleteOldJobsResponse,
    summary="Remove Old Jobs",
    description=(
        "Deletes job listings from the database based on relative time, specific date range, "
        "or truncates all jobs if truncate is set to true. Returns deleted job items."
    ),
)
async def delete_old_jobs(
    days: int | None = Query(
        None,
        ge=0,
        description="Number of days threshold. Jobs scraped older than this number of days will be deleted.",
    ),
    hours: int | None = Query(
        None,
        ge=0,
        description="Number of hours threshold. Jobs scraped older than this number of hours will be deleted.",
    ),
    minutes: int | None = Query(
        None,
        ge=0,
        description="Number of minutes threshold. Jobs scraped older than this number of minutes will be deleted.",
    ),
    start_date: str | None = Query(
        None,
        description="Start date/time (ISO format) for deletion range (inclusive). E.g. 2026-06-08T00:00:00",
    ),
    end_date: str | None = Query(
        None,
        description="End date/time (ISO format) for deletion range (inclusive). E.g. 2026-06-08T23:59:59",
    ),
    truncate: bool = Query(
        False,
        description="If true, deletes all jobs from the table.",
    ),
    repository: JobRepository = Depends(get_job_repository),
) -> DeleteOldJobsResponse:
    # Validate date range parameters if provided
    parsed_start = None
    parsed_end = None
    if start_date:
        try:
            # Replace trailing Z to allow simple fromisoformat parsing
            clean_start = start_date.replace("Z", "+00:00")
            parsed_start = datetime.fromisoformat(clean_start)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid start_date format. Use ISO 8601 format (e.g. YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ)",
            )
    if end_date:
        try:
            clean_end = end_date.replace("Z", "+00:00")
            parsed_end = datetime.fromisoformat(clean_end)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid end_date format. Use ISO 8601 format (e.g. YYYY-MM-DDTHH:MM:SS or YYYY-MM-DDTHH:MM:SSZ)",
            )

    logger.info(
        "Received request to clean up jobs: days=%s, hours=%s, minutes=%s, start_date=%s, end_date=%s, truncate=%s",
        days, hours, minutes, start_date, end_date, truncate
    )

    deleted_rows = repository.delete_old_jobs(
        days=days,
        hours=hours,
        minutes=minutes,
        start_date=parsed_start,
        end_date=parsed_end,
        truncate=truncate,
    )

    deleted_jobs = []
    for row in deleted_rows:
        tags_val = row.get("tags") or ""
        tags_list = tags_val.split(",") if tags_val else []

        job_item = JobItem(
            id=hashlib.md5(row.get("url", "").encode()).hexdigest(),
            title=row.get("title", ""),
            company=row.get("company") or "",
            url=row.get("url", ""),
            description=row.get("description") or "",
            location=row.get("location") or "",
            salary=row.get("salary") or "",
            source=row.get("source", ""),
            site=row.get("source", ""),
            tags=tags_list,
            scraped_at=row.get("scraped_at").isoformat() if hasattr(row.get("scraped_at"), "isoformat") else str(row.get("scraped_at")),
        )
        deleted_jobs.append(job_item)

    logger.info("Successfully deleted %d jobs", len(deleted_jobs))
    return DeleteOldJobsResponse(
        deleted_count=len(deleted_jobs),
        deleted_jobs=deleted_jobs,
    )
