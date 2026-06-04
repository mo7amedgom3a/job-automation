"""Application orchestrator for spider and Google searches."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from models.job import SearchRequest
from services.filters import is_blacklisted_company
from services.google_search import GoogleJobSearchService
from services.spider_runner import SpiderRunner
from config.settings import SITES, KEYWORDS, DEFAULT_MAX_CONCURRENT_SPIDERS, DEFAULT_INDEED_LIMIT, DEFAULT_MAX_PAGES

logger = logging.getLogger("job_aggregator.services.orchestrator")


class JobOrchestrator:
    """Coordinates custom spiders and Google dork searches."""

    def __init__(
        self,
        spider_runner: SpiderRunner | None = None,
        google_search_service: GoogleJobSearchService | None = None,
        max_concurrent_spiders: int = DEFAULT_MAX_CONCURRENT_SPIDERS,
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
        keywords = req.keywords or KEYWORDS
        

        is_remote = self._is_remote(req)
        location = self._location(req, is_remote)
        primary_country = req.countries[0].title() if req.countries else "Egypt"

        base_env_overrides = self._build_env_overrides(req, keywords)
        spiders_to_run = self._select_spiders(is_remote, primary_country, location, base_env_overrides)
        logger.info("Determined spiders to execute: %s", spiders_to_run)

        semaphore = asyncio.Semaphore(self.max_concurrent_spiders)

        async def run_spider(name: str) -> list[dict[str, Any]]:
            # Find spider config to check for site-specific keywords in settings
            cfg = next((s for s in SITES if s.name == name), None)
            
            # Use request keywords if user specified them; otherwise fall back to settings keywords if defined
            # If not defined in settings, use the fallback keywords.
            if req.keywords:
                spider_keywords = req.keywords
            elif cfg and cfg.keywords:
                spider_keywords = cfg.keywords
            else:
                spider_keywords = keywords
                
            spider_env = self._build_env_overrides(req, spider_keywords)
            # Propagate any other settings configured during selection
            for k, v in base_env_overrides.items():
                if k not in spider_env:
                    spider_env[k] = v
                    
            async with semaphore:
                return await self.spider_runner.run(name, spider_env)

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
            else:
                results.setdefault(spider_name, []).extend(result)

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
            "INDEED_LIMIT": str(DEFAULT_INDEED_LIMIT),
            "MAX_PAGES": str(DEFAULT_MAX_PAGES),
        }

    def _select_spiders(
        self,
        is_remote: bool,
        primary_country: str,
        location: str,
        env_overrides: dict[str, str],
    ) -> list[str]:
        # Filter sites that are enabled in settings config
        enabled_names = {site.name for site in SITES if site.enabled}

        if is_remote:
            # For remote searches, run all enabled general/regional version spiders,
            # but exclude the base 'linkedin' and 'indeed' configuration objects
            # as we run country-specific versions instead
            return [
                name for name in enabled_names
                if name not in {"linkedin", "indeed"}
            ]

        country = primary_country.lower().strip()
        location_lower = location.lower()
        selected = []

        if "egypt" in country or "cairo" in location_lower:
            selected = ["linkedin_eg", "indeed_eg"]
        elif "saudi" in country:
            selected = ["linkedin_sa", "indeed_sa"]
        elif "emirates" in country or "ae" in country or "uae" in country:
            selected = ["linkedin_ae", "indeed_ae"]
        elif "germany" in country:
            selected = ["linkedin_germany"]
        elif "poland" in country:
            selected = ["linkedin_poland"]
        elif "spain" in country or "barcelona" in location_lower:
            selected = ["linkedin_spain", "linkedin_barcelona"]
        elif "canada" in country:
            selected = ["linkedin_canada"]
        else:
            env_overrides["LINKEDIN_LOCATION"] = location
            env_overrides["INDEED_LOCATION"] = location
            selected = ["linkedin", "indeed"]

        return [name for name in selected if name in enabled_names]
