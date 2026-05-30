"""
Job Dork Search Service.

FastAPI service that builds advanced job dorks, searches DuckDuckGo, parses the
results into normalized jobs, and returns a compact response for n8n.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from scraper_api.cache import DeduplicationCache
    from scraper_api.dork_builder import DorkQueryBuilder
    from scraper_api.parser import JobResultParser
    from scraper_api.searcher import DuckDuckGoSearcher, JobSpySearcher, GoogleApiSearcher
except ModuleNotFoundError:  # pragma: no cover - local script fallback
    from cache import DeduplicationCache
    from dork_builder import DorkQueryBuilder
    from parser import JobResultParser
    from searcher import DuckDuckGoSearcher, JobSpySearcher, GoogleApiSearcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("job-dork-api")

app = FastAPI(
    title="Job Dork Search Service",
    description="Advanced job dork search via DuckDuckGo for n8n automation.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

dork_builder = DorkQueryBuilder()
searcher = DuckDuckGoSearcher()
parser = JobResultParser()
cache = DeduplicationCache()
jobspy_searcher = JobSpySearcher()
google_searcher = GoogleApiSearcher()


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
    location: str | None = "remote"
    countries: list[str] = Field(
        default_factory=lambda: ["egypt", "Middle East", "eu", "usa", "canada", "Germany", "france", "uk"]
    )
    job_type: str | None = None
    experience: str | None = None
    max_results: int = Field(default=50, ge=1, le=200)
    days_back: int = Field(default=1, ge=1, le=60)
    recent_hours: int | None = Field(default=24, ge=1, le=24 * 60)
    posted_today: bool = False
    strict_recent: bool = True
    sort_by_posted_at: bool = True
    reset_cache: bool = False

    # JobSpy specific parameters
    easy_apply: bool | None = None
    strict_country: bool = False
    linkedin_fetch_description: bool = False
    linkedin_company_ids: list[int] | None = None
    google_search_term: str | None = None
    distance: int | None = None
    proxies: list[str] | None = None
    enforce_annual_salary: bool | None = None
    user_agent: str | None = None
    ca_cert: str | None = None
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "job-dork-search",
        "time": datetime.utcnow().isoformat(),
    }


def is_within_24_hours(date_str: str, snippet: str = "") -> bool:
    import re
    if not date_str:
        text_to_check = snippet.lower()
    else:
        text_to_check = date_str.lower()
        
    # Positive indicators (definitely within 24 hours)
    if any(k in text_to_check for k in ["hour", "minute", "min", "second", "just now"]):
        match = re.search(r'(\d+)\s+hours?\s+ago', text_to_check)
        if match:
            hours = int(match.group(1))
            return hours <= 24
        return True
        
    # Negative indicators (definitely older than 24 hours)
    if any(k in text_to_check for k in ["day", "week", "month", "year", "yesterday"]):
        return False
        
    # Calendar dates
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    if any(m in text_to_check for m in months):
        return False
        
    return True


@app.post("/search", response_model=SearchResponse)
async def search_jobs(req: SearchRequest) -> SearchResponse:
    """
    Main endpoint — n8n calls this every 6 hours.
    Builds customized dork template queries → searches Google via Serper/SerpApi →
    filters results strictly within 24 hours → parses → deduplicates → returns.
    """
    start = time.time()

    if req.reset_cache:
        cache.clear()
        logger.info("Cache cleared by request")

    # 1. Build dork template queries (exactly one query per board/site requested)
    queries = dork_builder.build_template_queries(
        keywords=req.keywords,
        sites=req.job_sites,
        location=req.location,
    )
    logger.info(f"Built {len(queries)} template-based dork queries")

    # 2. Search all queries concurrently via Google API Searcher (with 24h filter)
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
        # Enrich raw results with metadata needed by the parser
        for r in res:
            r["_dork_query"] = q["query"]
            r["_dork_keyword"] = q["keyword"]
            r["_dork_site"] = q["site"]
            r["_dork_strategy"] = q["strategy"]
        raw_results.extend(res)
    logger.info(f"Google API Search: Got {len(raw_results)} total raw results")

    # 3. Post-filter results strictly within the past 24 hours
    filtered_raw_results = []
    discarded_count = 0
    for r in raw_results:
        if is_within_24_hours(r.get("date", ""), r.get("body", "")):
            filtered_raw_results.append(r)
        else:
            discarded_count += 1
    logger.info(f"Date post-filter: Retained {len(filtered_raw_results)} / {len(raw_results)} results (discarded {discarded_count} older than 24 hours)")
    raw_results = filtered_raw_results

    # 4. Parse each result into a structured job
    parsed = parser.parse_many(raw_results)

    # 5. Deduplicate against seen URLs
    jobs = []
    skipped = 0
    for job in parsed:
        if cache.is_seen(job["url"]):
            skipped += 1
            continue
        cache.mark_seen(job["url"])
        jobs.append(job)

    # 6. Sort by relevance score, cap at max_results
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
async def search_orchestrate(req: SearchRequest) -> dict[str, list[dict]]:
    """
    Orchestrate and aggregate isolated job searches across LinkedIn, Indeed, and Google Search API.
    Returns a dictionary of results grouped by source.
    """
    logger.info("Received Orchestrated Search request")
    try:
        from scraper_api.orchestrator import JobOrchestrator
    except ModuleNotFoundError:
        from orchestrator import JobOrchestrator
        
    orchestrator = JobOrchestrator()
    
    if req.reset_cache:
        orchestrator.cache.clear()
        logger.info("Cache cleared by request")
        
    results = await orchestrator.orchestrate(req)
    return results


@app.post("/search/jobspy", response_model=list[dict])
async def search_jobspy(req: SearchRequest) -> list[dict]:
    """
    Scrape jobs concurrently using JobSpy across multiple sites with optimized parameters.
    """
    logger.info("Received JobSpy search request")
    
    # 1. Map job sites to JobSpy expected values
    site_mapping = {
        "linkedin.com/jobs": "linkedin",
        "linkedin": "linkedin",
        "indeed.com/jobs": "indeed",
        "indeed": "indeed",
        "glassdoor.com": "glassdoor",
        "glassdoor": "glassdoor",
        "google.com": "google",
        "google": "google",
        "ziprecruiter.com": "zip_recruiter",
        "ziprecruiter": "zip_recruiter",
        "zip_recruiter": "zip_recruiter",
    }
    
    site_names = []
    for site in req.job_sites:
        mapped = site_mapping.get(site.lower().strip())
        if mapped:
            site_names.append(mapped)
            
    # Default to all key platforms if none specified or matched
    if not site_names:
        site_names = ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"]
        
    # 2. Map location constraints
    is_remote = (req.location == "remote")
    location_term = "remote" if is_remote else (req.location or "")
    
    # 3. Map time limits (hours_old)
    hours_old = 72  # Default to last 3 days
    if req.recent_hours:
        hours_old = req.recent_hours
    elif req.days_back:
        hours_old = req.days_back * 24

    # 4. Run the searcher asynchronously with optimized parameters
    results = await jobspy_searcher.search(
        keywords=req.keywords,
        site_name=site_names,
        location=location_term,
        results_wanted=req.max_results,
        hours_old=hours_old,
        is_remote=is_remote,
        countries=req.countries,
        strict_country=req.strict_country,
        job_type=req.job_type,
        easy_apply=req.easy_apply,
        linkedin_fetch_description=req.linkedin_fetch_description,
        linkedin_company_ids=req.linkedin_company_ids,
        google_search_term=req.google_search_term,
        distance=req.distance,
        proxies=req.proxies,
        enforce_annual_salary=req.enforce_annual_salary,
        user_agent=req.user_agent,
        ca_cert=req.ca_cert,
        description_format=req.description_format,
    )
    
    return results


@app.get("/queries/preview")
async def preview_queries(
    keywords: str = Query("devops,kubernetes,terraform"),
    sites: str = Query("linkedin.com/jobs,weworkremotely.com,greenhouse.io,lever.co"),
    location: str = Query("remote"),
    countries: str = Query("egypt,mena,eu,usa,canada"),
    job_type: str | None = Query(None),
    experience: str | None = Query(None),
    days_back: int = Query(1, ge=1, le=60),
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
async def batch_search(req: BatchSearchRequest) -> dict[str, Any]:
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
async def clear_cache() -> dict[str, Any]:
    count = cache.size()
    cache.clear()
    return {"cleared": count, "message": f"Removed {count} seen URLs"}


@app.get("/cache/stats")
async def cache_stats() -> dict[str, Any]:
    return {"seen_urls": cache.size(), "oldest_entry": cache.oldest()}


def _ddg_timelimit(days_back: int, recent_hours: int | None) -> str:
    if recent_hours is not None and recent_hours <= 24:
        return "d"
    if days_back <= 1:
        return "d"
    if days_back <= 7:
        return "w"
    return "m"


def _filter_recent_jobs(
    jobs: list[dict[str, Any]],
    recent_hours: int | None,
    posted_today: bool,
    strict_recent: bool,
) -> tuple[list[dict[str, Any]], int]:
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=recent_hours) if recent_hours else None
    filtered: list[dict[str, Any]] = []
    skipped = 0

    for job in jobs:
        posted_at = _parse_posted_at(job.get("posted_at"))
        if not posted_at:
            if strict_recent:
                skipped += 1
                continue
            filtered.append(job)
            continue

        if posted_today and posted_at.date() != now.date():
            skipped += 1
            continue

        if cutoff and posted_at < cutoff:
            skipped += 1
            continue

        filtered.append(job)

    return filtered, skipped


def _parse_posted_at(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
        return parsed
    except Exception:
        return None
