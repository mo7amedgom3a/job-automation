"""
Job Dork Search Service
FastAPI service that builds Google Dork queries, executes them via
DuckDuckGo (no API key needed), parses results, and returns structured jobs.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio
import hashlib
import time
import logging
import os
from datetime import datetime

from scraper_api.dork_builder import DorkQueryBuilder
from scraper_api.searcher import DuckDuckGoSearcher, JobSpySearcher
from scraper_api.parser import JobResultParser
from scraper_api.cache import DeduplicationCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Job Dork Search Service",
    description="Google Dork-powered job search via DuckDuckGo",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared singletons ────────────────────────────────────────────────────────
dork_builder = DorkQueryBuilder()
searcher     = DuckDuckGoSearcher()
parser       = JobResultParser()
cache        = DeduplicationCache()
jobspy_searcher = JobSpySearcher()


# ── Request / Response models ────────────────────────────────────────────────
class SearchRequest(BaseModel):
    keywords:      list[str] = ["devops", "kubernetes", "terraform"]
    job_sites:     list[str] = ["linkedin.com/jobs", "weworkremotely.com",
                                 "remotive.com", "indeed.com/jobs",
                                 "wellfound.com/jobs", "greenhouse.io"]
    location:      Optional[str] = "remote"
    countries:     list[str] = ["egypt", "mena", "eu", "usa", "canada"]
    job_type:      Optional[str] = None       # full-time, contract, freelance
    experience:    Optional[str] = None       # junior, mid, senior
    max_results:   int = 30
    days_back:     int = 14
    recent_hours:  Optional[int] = 24
    reset_cache:   bool = False               # flush seen URLs for fresh run

    # JobSpy specific parameters
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

class JobResult(BaseModel):
    id:          str
    title:       str
    company:     str
    url:         str
    description: str
    location:    str
    salary:      str
    source:      str
    dork_query:  str
    posted_at:   str
    score:       float                        # result ranking score

class SearchResponse(BaseModel):
    jobs:          list[JobResult]
    total_found:   int
    new_jobs:      int
    cached_skipped:int
    queries_run:   int
    duration_ms:   int
    timestamp:     str


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "job-dork-search", "time": datetime.utcnow().isoformat()}


@app.post("/search", response_model=SearchResponse)
async def search_jobs(req: SearchRequest):
    """
    Main endpoint — n8n calls this every 6 hours.
    Builds dork queries → searches DuckDuckGo → parses → deduplicates → returns.
    """
    start = time.time()

    if req.reset_cache:
        cache.clear()
        logger.info("Cache cleared by request")

    # 1. Build dork queries
    queries = dork_builder.build(
        keywords=req.keywords,
        sites=req.job_sites,
        location=req.location,
        job_type=req.job_type,
        experience=req.experience,
    )
    logger.info(f"Built {len(queries)} dork queries")

    # 2. Search all queries concurrently (with rate-limit semaphore)
    raw_results = await searcher.search_all(queries, max_per_query=10)
    logger.info(f"Got {len(raw_results)} raw results")

    # 3. Parse each result into a structured job
    parsed = parser.parse_many(raw_results)

    # 4. Deduplicate against seen URLs
    new_jobs = []
    skipped  = 0
    for job in parsed:
        if cache.is_seen(job["url"]):
            skipped += 1
            continue
        cache.mark_seen(job["url"])
        new_jobs.append(job)

    # 5. Sort by relevance score, cap at max_results
    new_jobs.sort(key=lambda j: j.get("score", 0), reverse=True)
    new_jobs = new_jobs[:req.max_results]

    duration = int((time.time() - start) * 1000)
    logger.info(f"Returning {len(new_jobs)} new jobs ({skipped} skipped) in {duration}ms")

    return SearchResponse(
        jobs           = [JobResult(**j) for j in new_jobs],
        total_found    = len(parsed),
        new_jobs       = len(new_jobs),
        cached_skipped = skipped,
        queries_run    = len(queries),
        duration_ms    = duration,
        timestamp      = datetime.utcnow().isoformat(),
    )


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
    sites: str    = Query("linkedin.com/jobs,weworkremotely.com"),
    location: str = Query("remote"),
):
    """Preview the dork queries that would be generated — useful for tuning."""
    kw_list   = [k.strip() for k in keywords.split(",")]
    site_list = [s.strip() for s in sites.split(",")]
    queries   = dork_builder.build(keywords=kw_list, sites=site_list, location=location)
    return {"queries": queries, "count": len(queries)}


@app.delete("/cache")
async def clear_cache():
    """Flush the deduplication cache — forces a full re-scan on next run."""
    count = cache.size()
    cache.clear()
    return {"cleared": count, "message": f"Removed {count} seen URLs"}


@app.get("/cache/stats")
async def cache_stats():
    return {"seen_urls": cache.size(), "oldest_entry": cache.oldest()}
