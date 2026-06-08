"""Search endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, BackgroundTasks

from cache.cache import DeduplicationCache
from dependencies import get_cache, get_google_job_search_service, get_orchestrator, get_job_repository
from models.job import SearchRequest, SearchResponse, JobSearchRequest, CountryGroup, PaginatedSearchResponse, SubAggregateRequest, CountryInfo, CountriesResponse
from repository.jobs import JobRepository
from services.google_search import GoogleJobSearchService
from services.orchestrator import JobOrchestrator
from config.settings import KEYWORDS 
logger = logging.getLogger("job_aggregator.routes.search")

router = APIRouter(prefix="/search", tags=["search"])


def resolve_country(job: dict) -> str:
    source = (job.get("source") or "").lower()
    
    # Direct source mappings
    if "eg" in source:
        return "Egypt"
    if "sa" in source:
        return "Saudi Arabia"
    if "ae" in source:
        return "United Arab Emirates"
    if "germany" in source:
        return "Germany"
    if "uk" in source:
        return "United Kingdom"
    if "poland" in source:
        return "Poland"
    if "canada" in source:
        return "Canada"
    if "spain" in source or "barcelona" in source:
        return "Spain"
        
    # Check location/tags
    loc = (job.get("location") or "").lower()
    tags = "".join(job.get("tags") or []).lower()
    
    countries_to_check = {
        "Egypt": ["egypt", "cairo", "alexandria"],
        "Saudi Arabia": ["saudi", "riyadh", "jeddah"],
        "United Arab Emirates": ["uae", "dubai", "abu dhabi", "united arab emirates", "emirates", "emarties"],
        "Germany": ["germany", "berlin", "munich", "frankfurt"],
        "Poland": ["poland", "warsaw", "krakow"],
        "Canada": ["canada", "toronto", "vancouver", "montreal"],
        "Spain": ["spain", "barcelona", "madrid"],
        "United States": ["usa", "united states", "us", "new york", "san francisco", "california"],
        "United Kingdom": ["uk", "united kingdom", "london", "england"],
    }
    
    for country, keywords in countries_to_check.items():
        if any(kw in loc for kw in keywords) or any(kw in tags for kw in keywords):
            return country
            
    return "Remote"


def clean_job_board_name(source: str) -> str:
    src = source.lower()
    if src.startswith("linkedin"):
        return "linkedin"
    if src.startswith("indeed"):
        return "indeed"
    return src


def is_job_remote(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    location = (job.get("location") or "").lower()
    tags = "".join(job.get("tags") or []).lower()
    source = (job.get("source") or "").lower()
    
    remote_sources = {"remoteok", "weworkremotely", "jobicy", "remotive", "himalayas", "trueup"}
    if source in remote_sources:
        return True
        
    return "remote" in title or "remote" in location or "remote" in tags


@router.post(
    "",
    response_model=PaginatedSearchResponse,
    summary="Search Aggregated Jobs",
    description="Retrieves aggregated job listings from the database, grouped by country and job board, returning remote jobs.",
)
async def search_jobs(
    req: JobSearchRequest,
    repository: JobRepository = Depends(get_job_repository),
) -> dict[str, Any]:
    import hashlib
    logger.info("Search request received: %s", req)
    db_jobs, total_count = repository.search_jobs(
        keywords=req.keywords,
        countries=req.countries,
        company=req.company,
        remote=req.remote,
        limit=req.limit,
        offset=req.offset,
    )
    
    grouped_data = {} # country -> job_board_name -> list of jobs
    
    for row in db_jobs:
        tags_val = row.get("tags") or ""
        tags_list = tags_val.split(",") if tags_val else []
        
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
            "tags": tags_list,
            "scraped_at": row.get("scraped_at").isoformat() if hasattr(row.get("scraped_at"), "isoformat") else str(row.get("scraped_at")),
        }
        
        # Filter remote/non-remote based on requested parameter
        if req.remote is not None:
            is_remote = is_job_remote(job_dict)
            if is_remote != req.remote:
                continue
            
        country = resolve_country(job_dict)
        board = clean_job_board_name(job_dict["source"])
        
        grouped_data.setdefault(country, {}).setdefault(board, []).append(job_dict)
        
    response_data = []
    for country_name, boards in grouped_data.items():
        board_groups = []
        for board_name, jobs_list in boards.items():
            # Sort jobs in each board by scraped_at DESC
            jobs_list.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)
            board_groups.append({
                "name": board_name,
                "jobs": jobs_list
            })
        response_data.append({
            "country": country_name,
            "job_boards": board_groups
        })
        
    return {
        "total": total_count,
        "limit": req.limit,
        "offset": req.offset,
        "results": response_data
    }


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


async def run_full_aggregation(
    orchestrator: JobOrchestrator,
    cache: DeduplicationCache,
    repository: JobRepository,
) -> None:
    logger.info("Starting background full aggregation run...")
    try:
        req = SearchRequest()
        # Live scrape / aggregation
        results = await orchestrator.orchestrate(req)
        flat_jobs = flatten_results(results, max_results=500, sources=["linkedin", "indeed", "google"])

        # Save all aggregated jobs to database (idempotent, duplicates handled via UNIQUE fingerprint)
        fingerprints = []
        for job in flat_jobs:
            source = job.get("source") or job.get("site") or "aggregate"
            fp = repository.fingerprint(job, source=source)
            fingerprints.append(fp)
            repository.save_job(job, source=source)

        # Cache the list of fingerprints for 1 hour (3600 seconds)
        import json
        cache_key = "aggregate:latest"
        cache.set_value(cache_key, json.dumps(fingerprints), 3600)
        logger.info("Background aggregation completed successfully. Saved %d jobs.", len(flat_jobs))
    except Exception as e:
        logger.error("Error in background aggregation task: %s", e, exc_info=True)


@router.post(
    "/aggregate",
    summary="Trigger Background Aggregation Process",
    description="Initiates background tasks to scrape jobs from all registered spiders and run the Google Search template. Caches results and saves them in the database.",
)
async def search_aggregate(
    background_tasks: BackgroundTasks,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
    repository: JobRepository = Depends(get_job_repository),
) -> dict[str, str]:
    logger.info("Initiating background job aggregation task")
    background_tasks.add_task(
        run_full_aggregation,
        orchestrator=orchestrator,
        cache=cache,
        repository=repository
    )
    return {"status": "initiated", "message": "Aggregation process started in the background."}


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


def find_matching_spiders(country: str, job_board: str) -> list[str]:
    c = country.lower().strip()
    jb = job_board.lower().strip()
    
    country_mappings = {
        "egypt": ["eg", "egypt"],
        "eg": ["eg", "egypt"],
        "saudi arabia": ["sa", "saudi"],
        "saudi": ["sa", "saudi"],
        "sa": ["sa", "saudi"],
        "united arab emirates": ["ae", "uae", "emirates"],
        "uae": ["ae", "uae", "emirates"],
        "ae": ["ae", "uae", "emirates"],
        "emirates": ["ae", "uae", "emirates"],
        "emarties": ["ae", "uae", "emirates"],
        "germany": ["germany", "de"],
        "de": ["germany", "de"],
        "poland": ["poland", "pl"],
        "pl": ["poland", "pl"],
        "spain": ["spain", "barcelona", "es"],
        "es": ["spain", "barcelona", "es"],
        "barcelona": ["barcelona", "spain"],
        "canada": ["canada", "ca"],
        "ca": ["canada", "ca"],
        "united kingdom": ["uk", "gb", "united kingdom"],
        "uk": ["uk", "gb", "united kingdom"],
        "gb": ["uk", "gb", "united kingdom"],
    }
    
    country_targets = country_mappings.get(c, [c])
    
    from config.settings import SITES
    matched = []
    for site in SITES:
        name = site.name.lower()
        if jb in name:
            parts = name.split('_')
            suffix = parts[1] if len(parts) > 1 else ""
            if any(t == suffix or t in parts for t in country_targets):
                matched.append(site.name)
            elif any(t in name for t in country_targets if len(t) > 2):
                matched.append(site.name)
                
    if not matched:
        for site in SITES:
            name = site.name.lower()
            if jb in name and any(t in name for t in country_targets):
                matched.append(site.name)
                
    return matched


async def run_sub_aggregation(
    country: str,
    job_board: str,
    orchestrator: JobOrchestrator,
    cache: DeduplicationCache,
    repository: JobRepository,
) -> None:
    logger.info("Starting background sub-aggregation for country=%s, job_board=%s...", country, job_board)
    try:
        from services.filters import is_blacklisted_company
        import json
        import asyncio

        spiders_to_run = find_matching_spiders(country, job_board)
        if not spiders_to_run:
            logger.warning("No matching spiders found for country=%s, job_board=%s", country, job_board)
            return

        req = SearchRequest(countries=[country])
        default_req_keywords = KEYWORDS
        use_settings_keywords = not req.keywords or req.keywords == default_req_keywords

        
        
        logger.info("Executing sub-aggregation spiders: %s", spiders_to_run)
        
        semaphore = asyncio.Semaphore(orchestrator.max_concurrent_spiders)

        async def run_spider(name: str) -> list[dict[str, Any]]:
            from config.settings import SITES
            cfg = next((s for s in SITES if s.name == name), None)
            
            if cfg and cfg.keywords and use_settings_keywords:
                spider_keywords = cfg.keywords
            else:
                spider_keywords = req.keywords or KEYWORDS
                
            spider_env = orchestrator._build_env_overrides(req, spider_keywords)
            async with semaphore:
                return await orchestrator.spider_runner.run(name, spider_env)

        spider_tasks = [run_spider(name) for name in spiders_to_run]
        task_results = await asyncio.gather(*spider_tasks, return_exceptions=True)
        
        results: dict[str, list[dict[str, Any]]] = {}
        for idx, spider_name in enumerate(spiders_to_run):
            result = task_results[idx]
            if isinstance(result, Exception):
                logger.error("Sub-aggregation spider '%s' failed: %s", spider_name, result)
                continue
            
            board_name = "linkedin" if "linkedin" in spider_name else ("indeed" if "indeed" in spider_name else spider_name)
            results.setdefault(board_name, []).extend(result)
            
        for source in results:
            results[source] = [
                job for job in results[source]
                if not is_blacklisted_company(job.get("company"))
            ]

        flat_jobs = flatten_results(results, max_results=500, sources=list(results.keys()))

        fingerprints = []
        for job in flat_jobs:
            source = job.get("source") or job.get("site") or "aggregate"
            fp = repository.fingerprint(job, source=source)
            fingerprints.append(fp)
            repository.save_job(job, source=source)

        cache_key = f"aggregate:sub:{country.lower()}:{job_board.lower()}:latest"
        cache.set_value(cache_key, json.dumps(fingerprints), 3600)
        logger.info("Background sub-aggregation for country=%s, job_board=%s completed successfully. Saved %d jobs.", country, job_board, len(flat_jobs))
    except Exception as e:
        logger.error("Error in background sub-aggregation task: %s", e, exc_info=True)


@router.post(
    "/aggregate/sub",
    summary="Trigger Background Sub-Aggregation Process",
    description="Initiates background tasks to scrape jobs from specific spiders matching target country and job board, saving results in the database.",
)
async def search_sub_aggregate(
    req: SubAggregateRequest,
    background_tasks: BackgroundTasks,
    orchestrator: JobOrchestrator = Depends(get_orchestrator),
    cache: DeduplicationCache = Depends(get_cache),
    repository: JobRepository = Depends(get_job_repository),
) -> dict[str, str]:
    logger.info("Initiating background job sub-aggregation task for country=%s, job_board=%s", req.country, req.job_board)
    background_tasks.add_task(
        run_sub_aggregation,
        country=req.country,
        job_board=req.job_board,
        orchestrator=orchestrator,
        cache=cache,
        repository=repository
    )
    return {"status": "initiated", "message": f"Sub-aggregation process started in the background for {req.job_board} in {req.country}."}


@router.get(
    "/countries",
    response_model=CountriesResponse,
    summary="Get Supported Countries and Job Boards",
    description="Returns a dictionary of supported countries, their display names, available job boards, and the specific spiders associated with them.",
)
async def get_supported_countries() -> CountriesResponse:
    # List of base country slugs/names mapped to display names
    country_list = [
        ("egypt", "Egypt"),
        ("saudi arabia", "Saudi Arabia"),
        ("united arab emirates", "United Arab Emirates"),
        ("germany", "Germany"),
        ("united kingdom", "United Kingdom"),
        ("poland", "Poland"),
        ("spain", "Spain"),
        ("canada", "Canada"),
    ]
    job_boards = ["linkedin", "indeed"]
    
    country_info_dict = {}
    for slug, display_name in country_list:
        matched_boards = []
        matched_spiders = []
        for jb in job_boards:
            spiders = find_matching_spiders(slug, jb)
            if spiders:
                matched_boards.append(jb)
                matched_spiders.extend(spiders)
        
        country_info_dict[slug] = CountryInfo(
            name=display_name,
            job_boards=matched_boards,
            spiders=matched_spiders
        )
        
    return CountriesResponse(countries=country_info_dict)
