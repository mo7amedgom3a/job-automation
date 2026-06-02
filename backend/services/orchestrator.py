"""Application orchestrator for spider and Google searches."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from models.job import SearchRequest
from services.filters import is_blacklisted_company
from services.google_search import GoogleJobSearchService
from services.spider_runner import SpiderRunner

logger = logging.getLogger("job_aggregator.services.orchestrator")


class JobOrchestrator:
    """Coordinates custom spiders and Google dork searches."""

    def __init__(
        self,
        spider_runner: SpiderRunner | None = None,
        google_search_service: GoogleJobSearchService | None = None,
        max_concurrent_spiders: int = 2,
    ) -> None:
        if spider_runner is None:
            from dependencies import get_spider_runner
            spider_runner = get_spider_runner()
        if google_search_service is None:
            from dependencies import get_google_job_search_service
            google_search_service = get_google_job_search_service()

        self.spider_runner = spider_runner
        self.google_search_service = google_search_service
        self.max_concurrent_spiders = max_concurrent_spiders

    async def orchestrate(self, req: SearchRequest) -> dict[str, list[dict[str, Any]]]:
        keywords = req.keywords or [
            "software engineer",
            "full stack",
            "backend",
            "DevOps",
            "cloud",
            "SRE",
            "AWS",
            "DevSecOps",
            "forward deployed engineer",
            "AI",
            "Engineer",
            "Developer",
            "Programmer",
            "web developer",
        ]

        is_remote = self._is_remote(req)
        location = self._location(req, is_remote)
        primary_country = req.countries[0].title() if req.countries else "Egypt"

        env_overrides = self._build_env_overrides(req, keywords)
        spiders_to_run = self._select_spiders(is_remote, primary_country, location, env_overrides)
        logger.info("Determined spiders to execute: %s", spiders_to_run)

        semaphore = asyncio.Semaphore(self.max_concurrent_spiders)

        async def run_spider(name: str) -> list[dict[str, Any]]:
            async with semaphore:
                return await self.spider_runner.run(name, env_overrides)

        spider_tasks = [run_spider(name) for name in spiders_to_run]
        google_task = self.google_search_service.search_jobs(
            keywords=keywords,
            sites=req.job_sites,
            location="remote",
            max_results=req.max_results,
            exclude_major_boards=True,
        )

        task_results = await asyncio.gather(*spider_tasks, google_task, return_exceptions=True)
        results: dict[str, list[dict[str, Any]]] = {"linkedin": [], "indeed": [], "google": []}

        google_result = task_results[-1]
        if isinstance(google_result, Exception):
            logger.error("Google search failed: %s", google_result)
        else:
            results["google"] = google_result

        for idx, spider_name in enumerate(spiders_to_run):
            result = task_results[idx]
            if isinstance(result, Exception):
                logger.error("Spider '%s' failed: %s", spider_name, result)
                continue
            if "linkedin" in spider_name:
                results["linkedin"].extend(result)
            elif "indeed" in spider_name:
                results["indeed"].extend(result)

        for source in results:
            results[source] = [
                job for job in results[source]
                if not is_blacklisted_company(job.get("company"))
            ]

        return results

    def _is_remote(self, req: SearchRequest) -> bool:
        if req.work_type == "remote":
            return True
        if req.work_type == "onsite":
            return False
        return (req.location == "remote") if req.location else True

    def _location(self, req: SearchRequest, is_remote: bool) -> str:
        if is_remote and (not req.location or req.location == "remote"):
            return "remote"
        return req.location or "Cairo"

    def _build_env_overrides(self, req: SearchRequest, keywords: list[str]) -> dict[str, str]:
        search_term = " OR ".join([f'"{keyword}"' if " " in keyword else keyword for keyword in keywords])
        hours_old = 24 if req.recent_hours == 24 else 72
        return {
            "LINKEDIN_KEYWORDS": search_term,
            "LINKEDIN_TPR": "r86400" if hours_old == 24 else "r259200",
            "INDEED_QUERY": search_term,
            "INDEED_FROMAGE": "1" if hours_old == 24 else "3",
            "INDEED_LIMIT": "50",
            "MAX_PAGES": "5",
        }

    def _select_spiders(
        self,
        is_remote: bool,
        primary_country: str,
        location: str,
        env_overrides: dict[str, str],
    ) -> list[str]:
        if is_remote:
            return [
                "linkedin_sa",
                "linkedin_eg",
                "linkedin_ae",
                "linkedin_barcelona",
                "linkedin_germany",
                "linkedin_poland",
                "linkedin_spain",
                "linkedin_canada",
                "indeed_eg",
                "indeed_sa",
                "indeed_ae",
            ]

        country = primary_country.lower().strip()
        location_lower = location.lower()
        if "egypt" in country or "cairo" in location_lower:
            return ["linkedin_eg", "indeed_eg"]
        if "saudi" in country:
            return ["linkedin_sa", "indeed_sa"]
        if "emirates" in country or "ae" in country or "uae" in country:
            return ["linkedin_ae", "indeed_ae"]
        if "germany" in country:
            return ["linkedin_germany"]
        if "poland" in country:
            return ["linkedin_poland"]
        if "spain" in country or "barcelona" in location_lower:
            return ["linkedin_spain", "linkedin_barcelona"]
        if "canada" in country:
            return ["linkedin_canada"]

        env_overrides["LINKEDIN_LOCATION"] = location
        env_overrides["INDEED_LOCATION"] = location
        return ["linkedin", "indeed"]
