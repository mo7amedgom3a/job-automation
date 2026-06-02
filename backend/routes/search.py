"""Search endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends

from cache.cache import DeduplicationCache
from dependencies import get_cache, get_google_job_search_service, get_orchestrator, get_job_repository
from models.job import SearchRequest, SearchResponse
from repository.jobs import JobRepository
from services.google_search import GoogleJobSearchService
from services.orchestrator import JobOrchestrator

logger = logging.getLogger("job_aggregator.routes.search")

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "",
    response_model=SearchResponse,
    summary="Google Dork Job Search",
    description="Executes template-based Google Search dorks using custom keywords, location, and target ATS domains. Restricts results based on recency and filters out blacklisted companies.",
)
async def search_jobs(
    req: SearchRequest,
    search_service: GoogleJobSearchService = Depends(get_google_job_search_service),
) -> SearchResponse:
    return await search_service.search(req)


@router.post(
    "/orchestrate",
    response_model=dict[str, list[dict]],
    summary="Orchestrate Spiders & Google Search",
    description="Runs concurrent country-specific scrapers (using Playwright) and Google Search queries in parallel. Restricts execution to spiders matching the target country and remote parameters.",
)
async def search_orchestrate(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
) -> dict[str, list[dict]]:
    logger.info("Received orchestrated search request")
    if req.reset_cache:
        cache.clear()
    return await orchestrator.orchestrate(req)


@router.post(
    "/aggregate",
    response_model=list[dict],
    summary="Flat Aggregated Search with 1-Hour Database Cache",
    description="Unified flat job list from LinkedIn, Indeed, and Google. Live-aggregated results are saved to the PostgreSQL database and cached for 1 hour. Subsequent matching requests load directly from the database.",
)
async def search_aggregate(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
    repository: JobRepository = Depends(get_job_repository),
) -> list[dict[str, Any]]:
    logger.info("Received flat aggregated search request")
    
    import json
    import hashlib

    # 1. Determine cache key based on search parameters
    req_data = req.model_dump(exclude={"reset_cache"})
    
    def normalize(val: Any) -> Any:
        if isinstance(val, list):
            return sorted([normalize(x) for x in val])
        elif isinstance(val, dict):
            return {k: normalize(v) for k, v in sorted(val.items())}
        return val

    normalized_data = normalize(req_data)
    serialized = json.dumps(normalized_data, sort_keys=True)
    cache_key = f"aggregate:cache:{hashlib.sha256(serialized.encode()).hexdigest()}"

    if req.reset_cache:
        cache.clear()
        cache.delete(cache_key)
    else:
        # Check if the query has been aggregated and cached in the last 1 hour
        cached_fingerprints_json = cache.get_value(cache_key)
        if cached_fingerprints_json:
            logger.info("Cache hit for search aggregate request. Querying jobs from database.")
            try:
                fingerprints = json.loads(cached_fingerprints_json)
                if isinstance(fingerprints, list):
                    db_jobs = repository.get_jobs_by_fingerprints(fingerprints)
                    # Convert to response dictionary and maintain cached order
                    jobs_map = {}
                    for row in db_jobs:
                        fp = row.get("fingerprint")
                        tags_val = row.get("tags") or ""
                        job_dict = {
                            "id": hashlib.md5(row.get("url", "").encode()).hexdigest(),
                            "title": row.get("title", ""),
                            "company": row.get("company", ""),
                            "url": row.get("url", ""),
                            "description": row.get("description", ""),
                            "location": row.get("location", ""),
                            "salary": row.get("salary", ""),
                            "source": row.get("source", ""),
                            "site": row.get("source", ""),
                            "tags": tags_val.split(",") if tags_val else [],
                            "scraped_at": row.get("scraped_at").isoformat() if hasattr(row.get("scraped_at"), "isoformat") else str(row.get("scraped_at")),
                        }
                        jobs_map[fp] = job_dict
                    
                    ordered_jobs = [jobs_map[fp] for fp in fingerprints if fp in jobs_map]
                    if ordered_jobs:
                        logger.info("Returning %d cached jobs from database", len(ordered_jobs))
                        return ordered_jobs
            except Exception as e:
                logger.error("Failed to retrieve jobs from cache/database: %s. Falling back to live scrape.", e)

    # 2. Live scrape / aggregation
    results = await orchestrator.orchestrate(req)
    flat_jobs = flatten_results(results, max_results=req.max_results, sources=["linkedin", "indeed", "google"])

    # 3. Save all aggregated jobs to database (idempotent, duplicates handled via UNIQUE fingerprint)
    fingerprints = []
    for job in flat_jobs:
        fp = repository.fingerprint(job)
        fingerprints.append(fp)
        source = job.get("site") or job.get("source") or "aggregate"
        repository.save_job(job, source=source)

    # 4. Cache the list of fingerprints for 1 hour (3600 seconds)
    try:
        cache.set_value(cache_key, json.dumps(fingerprints), 3600)
        logger.info("Cached %d job fingerprints for 1 hour", len(fingerprints))
    except Exception as e:
        logger.error("Failed to write to cache: %s", e)

    return flat_jobs


@router.post(
    "/jobspy",
    response_model=list[dict],
    summary="Legacy JobSpy Search Compatibility Route",
    description="A flattened list containing jobs specifically aggregated from LinkedIn and Indeed. Compatible with legacy client applications.",
)
async def search_jobspy(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
) -> list[dict[str, Any]]:
    logger.info("Routing legacy search/jobspy endpoint to custom spider engine")
    if req.reset_cache:
        cache.clear()

    results = await orchestrator.orchestrate(req)
    return flatten_results(results, max_results=req.max_results, sources=["linkedin", "indeed"])


def flatten_results(
    results: dict[str, list[dict[str, Any]]],
    max_results: int,
    sources: list[str],
) -> list[dict[str, Any]]:
    unified: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for source in sources:
        for job in results.get(source, []):
            url = job.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            job["site"] = source
            unified.append(job)

    return unified[:max_results]
