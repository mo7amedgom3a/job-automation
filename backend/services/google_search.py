"""Google dork search service."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from cache.cache import DeduplicationCache
from dork_builder import DorkQueryBuilder
from google_api_search_engine import GoogleApiSearcher
from models.job import JobResult, SearchRequest, SearchResponse
from parser import JobResultParser
from services.filters import is_blacklisted_company, is_within_24_hours

logger = logging.getLogger("job_aggregator.services.google_search")


class GoogleJobSearchService:
    """Runs Google API dork searches and normalizes the results."""

    def __init__(
        self,
        dork_builder: DorkQueryBuilder,
        google_searcher: GoogleApiSearcher,
        parser: JobResultParser,
        cache: DeduplicationCache,
    ) -> None:
        self.dork_builder = dork_builder
        self.google_searcher = google_searcher
        self.parser = parser
        self.cache = cache

    async def search(self, req: SearchRequest) -> SearchResponse:
        start = time.time()

        if req.reset_cache:
            self.cache.clear()
            logger.info("Cache cleared by request")

        raw_results, queries_run, recency_skipped = await self.search_raw(
            keywords=req.keywords,
            sites=req.job_sites,
            location=req.location or "remote",
            max_results_per_query=20,
        )

        parsed = self.parser.parse_many(raw_results)
        jobs: list[dict[str, Any]] = []
        skipped = 0

        for job in parsed:
            if is_blacklisted_company(job.get("company")):
                continue
            if self.cache.is_seen(job["url"]):
                skipped += 1
                continue
            self.cache.mark_seen(job["url"])
            jobs.append(job)

        jobs.sort(key=lambda j: j.get("score", 0), reverse=True)
        jobs = jobs[: req.max_results]

        duration = int((time.time() - start) * 1000)
        logger.info("Returning %d new jobs (%d skipped) in %dms", len(jobs), skipped, duration)

        return SearchResponse(
            jobs=[JobResult(**job) for job in jobs],
            total_found=len(parsed),
            new_jobs=len(jobs),
            cached_skipped=skipped,
            recency_skipped=recency_skipped,
            queries_run=queries_run,
            duration_ms=duration,
            timestamp=datetime.utcnow().isoformat(),
        )

    async def search_jobs(
        self,
        keywords: list[str],
        sites: list[str],
        location: str,
        max_results: int,
        exclude_major_boards: bool = False,
    ) -> list[dict[str, Any]]:
        raw_results, _, _ = await self.search_raw(
            keywords=keywords,
            sites=self._filter_sites(sites) if exclude_major_boards else sites,
            location=location,
            max_results_per_query=max_results,
        )

        parsed_jobs = self.parser.parse_many(raw_results)
        deduped: list[dict[str, Any]] = []
        for job in parsed_jobs:
            if is_blacklisted_company(job.get("company")):
                continue
            if self.cache.is_seen(job["url"]):
                continue
            self.cache.mark_seen(job["url"])
            deduped.append(job)
        return deduped

    async def search_raw(
        self,
        keywords: list[str],
        sites: list[str],
        location: str,
        max_results_per_query: int,
    ) -> tuple[list[dict[str, Any]], int, int]:
        queries = self.dork_builder.build_template_queries(
            keywords=keywords,
            sites=sites,
            location=location,
        )
        logger.info("Built %d template-based dork queries", len(queries))

        tasks = [
            self.google_searcher.search(q["query"], max_results=max_results_per_query)
            for q in queries
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        raw_results: list[dict[str, Any]] = []
        for query, result in zip(queries, results_nested):
            if isinstance(result, Exception):
                logger.warning("Google API search failed for query %s: %s", query["query"][:60], result)
                continue
            for item in result:
                item["_dork_query"] = query["query"]
                item["_dork_keyword"] = query["keyword"]
                item["_dork_site"] = query["site"]
                item["_dork_strategy"] = query["strategy"]
            raw_results.extend(result)

        filtered_raw_results = [
            item for item in raw_results if is_within_24_hours(item.get("date", ""), item.get("body", ""))
        ]
        recency_skipped = len(raw_results) - len(filtered_raw_results)
        logger.info(
            "Date post-filter retained %d / %d results",
            len(filtered_raw_results),
            len(raw_results),
        )
        return filtered_raw_results, len(queries), recency_skipped

    def _filter_sites(self, sites: list[str]) -> list[str]:
        excluded_keywords = {"linkedin", "indeed", "google", "glassdoor", "ziprecruiter.com"}
        filtered = [
            site for site in sites
            if not any(excluded in site.lower().strip() for excluded in excluded_keywords)
        ]
        if filtered:
            return filtered
        return [
            "weworkremotely.com",
            "remotive.com",
            "wellfound.com",
            "greenhouse.io",
            "job-boards.greenhouse.io",
            "remoteok.io",
            "lever.co",
            "workable.com",
            "jobs.ashbyhq.com",
            "jobicy.com",
            "remote.co",
        ]
