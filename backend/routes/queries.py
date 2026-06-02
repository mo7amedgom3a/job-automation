"""Query preview and batch search endpoints."""

from __future__ import annotations

from typing import Any

import asyncio
from fastapi import APIRouter, Depends, Query

from dependencies import get_dork_builder, get_google_searcher, get_parser
from dork_builder import DorkQueryBuilder
from google_api_search_engine import GoogleApiSearcher
from models.job import BatchSearchRequest
from parser import JobResultParser

router = APIRouter(tags=["queries"])


@router.get(
    "/queries/preview",
    summary="Preview Query Dorks",
    description="Builds and outputs list of Google Search Dork queries constructed from search keywords, location constraints, countries, and date filters without running them.",
)
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


@router.post(
    "/batch-search",
    summary="Batch Google Search",
    description="Runs a list of custom Google search queries in parallel, parses the output, and returns normalized job result items.",
)
async def batch_search(
    req: BatchSearchRequest,
    google_searcher: GoogleApiSearcher = Depends(get_google_searcher),
    parser: JobResultParser = Depends(get_parser),
) -> dict[str, Any]:
    tasks = [
        google_searcher.search(query, max_results=req.max_results)
        for query in req.queries
    ]
    results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    raw_results: list[dict[str, Any]] = []
    for query, result in zip(req.queries, results_nested):
        if isinstance(result, Exception):
            continue
        for item in result:
            item["_dork_query"] = query
            item["_dork_keyword"] = ""
            item["_dork_site"] = "custom"
            item["_dork_strategy"] = "custom_google_api"
        raw_results.extend(result)

    jobs = parser.parse_many(raw_results)
    return {
        "jobs": jobs[: req.max_results],
        "results": raw_results,
        "organic": raw_results,
        "count": len(raw_results),
        "queries_run": len(req.queries),
    }
