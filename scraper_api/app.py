"""
Job Dork and Scraper Aggregator Service.
FastAPI application to manage parallel custom spiders, dorks, and Google API searches.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from scraper_api.cache import DeduplicationCache
    from scraper_api.dork_builder import DorkQueryBuilder
    from scraper_api.parser import JobResultParser
    from scraper_api.searcher import DuckDuckGoSearcher, GoogleApiSearcher
    from scraper_api.orchestrator import JobOrchestrator
except ModuleNotFoundError:
    from cache import DeduplicationCache
    from dork_builder import DorkQueryBuilder
    from parser import JobResultParser
    from searcher import DuckDuckGoSearcher, GoogleApiSearcher
    from orchestrator import JobOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job-dork-api")

app = FastAPI(
    title="Job Aggregator Service",
    description="Unified API aggregating Google Dorks and custom concurrent Playwright spiders.",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared Singletons ───────────────────────────────────────────────────────
_dork_builder = DorkQueryBuilder()
_searcher = DuckDuckGoSearcher()
_parser = JobResultParser()
_cache = DeduplicationCache()
_google_searcher = GoogleApiSearcher()


# ── Dependency Injection Providers ──────────────────────────────────────────
def get_dork_builder() -> DorkQueryBuilder:
    return _dork_builder


def get_searcher() -> DuckDuckGoSearcher:
    return _searcher


def get_parser() -> JobResultParser:
    return _parser


def get_cache() -> DeduplicationCache:
    return _cache


def get_google_searcher() -> GoogleApiSearcher:
    return _google_searcher


def get_orchestrator() -> JobOrchestrator:
    return JobOrchestrator()


# ── Request / Response Models ───────────────────────────────────────────────
class SearchRequest(BaseModel):
    keywords: list[str] = Field(
        default_factory=lambda: [
            "devops",
            "kubernetes",
            "terraform",
            "aws",
            "python",
            "golang",
            "fastapi",
        ]
    )
    job_sites: list[str] = Field(
        default_factory=lambda: [
            "linkedin.com/jobs",
            "weworkremotely.com",
            "remotive.com",
            "indeed.com/jobs",
            "wellfound.com",
            "greenhouse.io",
            "lever.co",
            "workable.com",
            "jobs.ashbyhq.com",
            "jobicy.com",
        ]
    )
    work_type: Optional[str] = None
    location: Optional[str] = "remote"
    countries: list[str] = Field(
        default_factory=lambda: ["egypt", "Middle East", "eu", "usa", "canada", "Germany", "france", "uk"]
    )
    job_type: Optional[str] = None
    experience: Optional[str] = None
    max_results: int = Field(default=50, ge=1, le=200)
    days_back: int = Field(default=1, ge=1, le=60)
    recent_hours: Optional[int] = Field(default=24, ge=1, le=24 * 60)
    posted_today: bool = False
    strict_recent: bool = True
    sort_by_posted_at: bool = True
    reset_cache: bool = False

    # Dynamic search overrides
    easy_apply: Optional[bool] = None
    strict_country: bool = False
    linkedin_fetch_description: bool = False
    linkedin_company_ids: Optional[list[int]] = None
    google_search_term: Optional[str] = None
    distance: Optional[int] = None
    proxies: Optional[list[str]] = None
    enforce_annual_salary: Optional[bool] = None
    user_agent: Optional[str] = None
    ca_cert: Optional[str] = None
    description_format: str = "markdown"


class BatchSearchRequest(BaseModel):
    queries: list[str] = Field(..., min_length=1, max_length=100)
    max_results: int = Field(default=25, ge=1, le=100)


class JobResult(BaseModel):
    id: str
    title: str
    company: str
    url: str
    description: str
    location: str
    salary: str
    source: str
    dork_query: str
    posted_at: str
    score: float


class SearchResponse(BaseModel):
    jobs: list[JobResult]
    total_found: int
    new_jobs: int
    cached_skipped: int
    recency_skipped: int
    queries_run: int
    duration_ms: int
    timestamp: str


# ── Helpers ─────────────────────────────────────────────────────────────────
def is_within_24_hours(date_str: str, snippet: str = "") -> bool:
    import re
    if not date_str:
        text_to_check = snippet.lower()
    else:
        text_to_check = date_str.lower()
        
    if any(k in text_to_check for k in ["hour", "minute", "min", "second", "just now"]):
        match = re.search(r'(\d+)\s+hours?\s+ago', text_to_check)
        if match:
            hours = int(match.group(1))
            return hours <= 24
        return True
        
    if any(k in text_to_check for k in ["day", "week", "month", "year", "yesterday"]):
        return False
        
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    if any(m in text_to_check for m in months):
        return False
        
    return True


# ── Endpoints ───────────────────────────────────────────────────────────────
@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "job-aggregator-service",
        "time": datetime.utcnow().isoformat(),
    }


@app.post("/search", response_model=SearchResponse)
async def search_jobs(
    req: SearchRequest,
    dork_builder: DorkQueryBuilder = Depends(get_dork_builder),
    google_searcher: GoogleApiSearcher = Depends(get_google_searcher),
    parser: JobResultParser = Depends(get_parser),
    cache: DeduplicationCache = Depends(get_cache),
) -> SearchResponse:
    """
    Dork template query searcher via Google API.
    """
    start = time.time()

    if req.reset_cache:
        cache.clear()
        logger.info("Cache cleared by request")

    queries = dork_builder.build_template_queries(
        keywords=req.keywords,
        sites=req.job_sites,
        location=req.location,
    )
    logger.info(f"Built {len(queries)} template-based dork queries")

    import asyncio
    tasks = [
        google_searcher.search(q["query"], max_results=20)
        for q in queries
    ]
    results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    raw_results = []
    for q, res in zip(queries, results_nested):
        if isinstance(res, Exception):
            logger.warning(f"Google API search failed for query: {q['query'][:60]} — {res}")
            continue
        for r in res:
            r["_dork_query"] = q["query"]
            r["_dork_keyword"] = q["keyword"]
            r["_dork_site"] = q["site"]
            r["_dork_strategy"] = q["strategy"]
        raw_results.extend(res)
    logger.info(f"Google API Search: Got {len(raw_results)} total raw results")

    filtered_raw_results = []
    discarded_count = 0
    for r in raw_results:
        if is_within_24_hours(r.get("date", ""), r.get("body", "")):
            filtered_raw_results.append(r)
        else:
            discarded_count += 1
    logger.info(f"Date post-filter: Retained {len(filtered_raw_results)} / {len(raw_results)} results (discarded {discarded_count} older than 24 hours)")
    raw_results = filtered_raw_results

    parsed = parser.parse_many(raw_results)

    jobs = []
    skipped = 0
    blacklist = [
        "crossing hurdles", "turing", "confidential", "confidential careers",
        "micro1", "canonical", "naphora games group", "meridial marketplace",
        "by invisible", "invisible", "siira", "proxify", "dataannotation",
        "mindrift", "mercor", "jobgether"
    ]
    
    def is_scam(company_name: str) -> bool:
        if not company_name:
            return False
        name_lower = company_name.lower().strip()
        return any(scam in name_lower for scam in blacklist)

    for job in parsed:
        if is_scam(job.get("company")):
            continue
        if cache.is_seen(job["url"]):
            skipped += 1
            continue
        cache.mark_seen(job["url"])
        jobs.append(job)

    jobs.sort(key=lambda j: j.get("score", 0), reverse=True)
    jobs = jobs[:req.max_results]

    duration = int((time.time() - start) * 1000)
    logger.info(f"Returning {len(jobs)} new jobs ({skipped} skipped) in {duration}ms")

    return SearchResponse(
        jobs=[JobResult(**job) for job in jobs],
        total_found=len(parsed),
        new_jobs=len(jobs),
        cached_skipped=skipped,
        recency_skipped=discarded_count,
        queries_run=len(queries),
        duration_ms=duration,
        timestamp=datetime.utcnow().isoformat(),
    )


@app.post("/search/orchestrate", response_model=dict[str, list[dict]])
async def search_orchestrate(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
) -> dict[str, list[dict]]:
    """
    Orchestrate and aggregate isolated job searches concurrently across custom spiders in parallel.
    Groups results by source (e.g. linkedin, indeed, google).
    """
    logger.info("Received Orchestrated Search request")
    if req.reset_cache:
        cache.clear()
        logger.info("Cache cleared by request")
        
    results = await orchestrator.orchestrate(req)
    return results


@app.post("/search/aggregate", response_model=list[dict])
async def search_aggregate(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
) -> list[dict]:
    """
    Aggregate all jobs from all custom spiders in parallel, presenting a unified,
    flat list of jobs sorted and filtered strictly to user requirements.
    """
    logger.info("Received flat Aggregated Search request")
    if req.reset_cache:
        cache.clear()
        logger.info("Cache cleared by request")
        
    results = await orchestrator.orchestrate(req)
    
    # Flatten parallel spider runs into a single list
    unified_list = []
    seen_urls = set()
    
    for source in ["linkedin", "indeed", "google"]:
        if source in results:
            for job in results[source]:
                url = job.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    job["site"] = source
                    unified_list.append(job)
                    
    # Cap to max results requested
    if req.max_results:
        unified_list = unified_list[:req.max_results]
        
    logger.info(f"Returning {len(unified_list)} flat unified aggregated jobs.")
    return unified_list


@app.post("/search/jobspy", response_model=list[dict])
async def search_jobspy(
    req: SearchRequest,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
) -> list[dict]:
    """
    Drop-in compatibility route for legacy search/jobspy.
    Routes to the new high-performance custom parallel spider engine dynamically.
    """
    logger.info("Routing legacy search/jobspy endpoint to parallel custom spiders engine.")
    if req.reset_cache:
        cache.clear()
        
    results = await orchestrator.orchestrate(req)
    
    # Flatten the result dictionary {linkedin: [...], indeed: [...]} into a single list
    combined = []
    for source in ["linkedin", "indeed"]:
        if source in results:
            for job in results[source]:
                job["site"] = source
                combined.append(job)
                
    return combined[:req.max_results]


@app.get("/queries/preview")
async def preview_queries(
    keywords: str = Query("devops,kubernetes,terraform"),
    sites: str = Query("linkedin.com/jobs,weworkremotely.com,greenhouse.io,lever.co"),
    location: str = Query("remote"),
    countries: str = Query("egypt,mena,eu,usa,canada"),
    job_type: str | None = Query(None),
    experience: str | None = Query(None),
    days_back: int = Query(1, ge=1, le=60),
    dork_builder: DorkQueryBuilder = Depends(get_dork_builder),
) -> dict[str, Any]:
    kw_list = [item.strip() for item in keywords.split(",") if item.strip()]
    site_list = [item.strip() for item in sites.split(",") if item.strip()]
    country_list = [item.strip() for item in countries.split(",") if item.strip()]
    queries = dork_builder.build(
        keywords=kw_list,
        sites=site_list,
        location=location,
        countries=country_list,
        job_type=job_type,
        experience=experience,
        days_back=days_back,
    )
    return {"queries": queries, "count": len(queries)}


@app.post("/batch-search")
async def batch_search(
    req: BatchSearchRequest,
    searcher: DuckDuckGoSearcher = Depends(get_searcher),
    parser: JobResultParser = Depends(get_parser),
) -> dict[str, Any]:
    query_dicts = [
        {"query": query, "keyword": "", "site": "custom", "strategy": "custom"}
        for query in req.queries
    ]
    raw_results = await searcher.search_all(query_dicts, max_per_query=req.max_results)
    jobs = parser.parse_many(raw_results)
    return {
        "jobs": jobs[: req.max_results],
        "results": raw_results,
        "organic": raw_results,
        "count": len(raw_results),
        "queries_run": len(query_dicts),
    }


@app.delete("/cache")
async def clear_cache(cache: DeduplicationCache = Depends(get_cache)) -> dict[str, Any]:
    count = cache.size()
    cache.clear()
    return {"cleared": count, "message": f"Removed {count} seen URLs"}


@app.get("/cache/stats")
async def cache_stats(cache: DeduplicationCache = Depends(get_cache)) -> dict[str, Any]:
    return {"seen_urls": cache.size(), "oldest_entry": cache.oldest()}
