"""Orchestrator service layer to aggregate and isolate job searches."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List
from datetime import datetime, timedelta
import re

from jobspy import scrape_jobs
import pandas as pd

try:
    from scraper_api.dork_builder import DorkQueryBuilder
    from scraper_api.google_api_search_engine import GoogleApiSearcher
    from scraper_api.parser import JobResultParser
    from scraper_api.cache import DeduplicationCache
except ModuleNotFoundError:
    from dork_builder import DorkQueryBuilder
    from google_api_search_engine import GoogleApiSearcher
    from parser import JobResultParser
    from cache import DeduplicationCache

logger = logging.getLogger("scraper-orchestrator")


class JobOrchestrator:
    """Orchestrates job search aggregation across LinkedIn, Indeed, and Google Search API."""

    def __init__(self) -> None:
        self.dork_builder = DorkQueryBuilder()
        self.google_searcher = GoogleApiSearcher()
        self.parser = JobResultParser()
        self.cache = DeduplicationCache()

    async def orchestrate(self, req: Any) -> Dict[str, List[Dict[str, Any]]]:
        """
        Orchestrates and isolates searches for LinkedIn, Indeed, and Google Search.
        """
        # Load keywords
        keywords = req.keywords if req.keywords else [
            "software engineer", "full stack", "backend", "DevOps", 
            "cloud", "SRE", "AWS", "DevSecOps", "forward deployed engineer"
        ]

        # Determine if remote
        is_remote = (req.location == "remote") if req.location else True
        location_val = "remote" if is_remote else (req.location or "Cairo")

        # Determine country constraints for JobSpy
        primary_country = "Egypt"
        if req.countries:
            primary_country = req.countries[0].title()

        results: Dict[str, List[Dict[str, Any]]] = {
            "linkedin": [],
            "indeed": [],
            "google": []
        }

        # Concurrently launch isolated searches
        tasks = []
        
        # 1. Isolated LinkedIn JobSpy Search
        tasks.append(self._search_linkedin_jobspy(
            keywords=keywords,
            location=location_val,
            is_remote=is_remote,
            country=primary_country,
            max_results=req.max_results,
            hours_old=24 if req.recent_hours == 24 else 72
        ))

        # 2. Isolated Indeed JobSpy Search
        tasks.append(self._search_indeed_jobspy(
            keywords=keywords,
            location=location_val,
            is_remote=is_remote,
            country=primary_country,
            max_results=req.max_results,
            hours_old=24 if req.recent_hours == 24 else 72
        ))

        # 3. Google Search API (using dork templates with 24h filter)
        tasks.append(self._search_google_dork(
            keywords=keywords,
            sites=req.job_sites,
            location=location_val,
            max_results=req.max_results
        ))

        # Wait for all tasks to complete
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Parse task responses
        if not isinstance(task_results[0], Exception):
            results["linkedin"] = task_results[0]
        else:
            logger.error(f"Orchestrator: LinkedIn search failed: {task_results[0]}")

        if not isinstance(task_results[1], Exception):
            results["indeed"] = task_results[1]
        else:
            logger.error(f"Orchestrator: Indeed search failed: {task_results[1]}")

        if not isinstance(task_results[2], Exception):
            results["google"] = task_results[2]
        else:
            logger.error(f"Orchestrator: Google search failed: {task_results[2]}")

        return results

    async def _search_linkedin_jobspy(
        self,
        keywords: List[str],
        location: str,
        is_remote: bool,
        country: str,
        max_results: int,
        hours_old: int
    ) -> List[Dict[str, Any]]:
        """Isolates the LinkedIn JobSpy scraper execution to prevent session conflicts."""
        loop = asyncio.get_event_loop()
        search_term = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])

        def _run():
            params = {
                "site_name": ["linkedin"],
                "search_term": search_term,
                "results_wanted": max_results,
                "hours_old": hours_old,
            }
            if is_remote:
                params["is_remote"] = True
                params["location"] = country if country != "Egypt" else "worldwide"
            else:
                params["location"] = location
                params["location_linkedin"] = country

            logger.info(f"Orchestrator: Starting LinkedIn JobSpy with parameters: {params}")
            try:
                df = scrape_jobs(**params)
                if df is None or df.empty:
                    return []
                return self._parse_jobspy_df(df)
            except Exception as e:
                logger.error(f"Orchestrator: LinkedIn JobSpy execution failed: {e}")
                return []

        return await loop.run_in_executor(None, _run)

    async def _search_indeed_jobspy(
        self,
        keywords: List[str],
        location: str,
        is_remote: bool,
        country: str,
        max_results: int,
        hours_old: int
    ) -> List[Dict[str, Any]]:
        """Isolates the Indeed JobSpy scraper execution to prevent session conflicts."""
        loop = asyncio.get_event_loop()
        search_term = " OR ".join([f'"{k}"' if " " in k else k for k in keywords])

        def _run():
            params = {
                "site_name": ["indeed"],
                "search_term": search_term,
                "results_wanted": max_results,
                "hours_old": 24 if hours_old == 24 else 72,
                "country_indeed": country
            }
            resolved_loc = location
            indeed_is_remote = is_remote

            if country in ("Egypt", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"):
                if is_remote:
                    resolved_loc = country
                    indeed_is_remote = False
                elif not location:
                    resolved_loc = country

            if resolved_loc:
                params["location"] = resolved_loc
                
            if indeed_is_remote:
                params["is_remote"] = True

            logger.info(f"Orchestrator: Starting Indeed JobSpy with parameters: {params}")
            try:
                df = scrape_jobs(**params)
                if df is None or df.empty:
                    return []
                return self._parse_jobspy_df(df)
            except Exception as e:
                logger.error(f"Orchestrator: Indeed JobSpy execution failed: {e}")
                return []

        return await loop.run_in_executor(None, _run)

    async def _search_google_dork(
        self,
        keywords: List[str],
        sites: List[str],
        location: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        # Exclude LinkedIn, Indeed, Glassdoor, and Google search engine domain from target search sites
        excluded_keywords = {"linkedin", "indeed", "google", "glassdoor", "ziprecruiter.com"}
        
        filtered_sites = []
        for s in sites:
            s_clean = s.lower().strip()
            if not any(ek in s_clean for ek in excluded_keywords):
                filtered_sites.append(s)
                
        # If no other boards are specified or left, default to a robust set of premium remote/onsite job boards
        if not filtered_sites:
            filtered_sites = [
                "weworkremotely.com",
                "remotive.com",
                "wellfound.com",
                "greenhouse.io",
                "lever.co",
                "workable.com",
                "jobs.ashbyhq.com",
                "jobicy.com",
                "remote.co"
            ]

        logger.info(f"Orchestrator: Google Dork Search targeting sites: {filtered_sites}")

        queries = self.dork_builder.build_template_queries(
            keywords=keywords,
            sites=filtered_sites,
            location="remote",
        )
        logger.info(f"Orchestrator: Built {len(queries)} Google template queries.")

        tasks = [
            self.google_searcher.search(q["query"], max_results=max_results)
            for q in queries
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        raw_results = []
        for q, res in zip(queries, results_nested):
            if isinstance(res, Exception):
                logger.warning(f"Orchestrator: Google API search failed for query: {q['query'][:60]} — {res}")
                continue
            for r in res:
                r["_dork_query"] = q["query"]
                r["_dork_keyword"] = q["keyword"]
                r["_dork_site"] = q["site"]
                r["_dork_strategy"] = q["strategy"]
            raw_results.extend(res)

        # Apply strict 24-hour post-filtering
        filtered_raw_results = []
        for r in raw_results:
            if self._is_within_24_hours(r.get("date", ""), r.get("body", "")):
                filtered_raw_results.append(r)
        
        logger.info(f"Orchestrator: Retained {len(filtered_raw_results)} / {len(raw_results)} Google results after 24h post-filtering.")
        
        # Parse into structured normalized job dicts
        parsed_jobs = self.parser.parse_many(filtered_raw_results)
        
        # Cache filtering & Deduplication
        deduped = []
        for job in parsed_jobs:
            if self.cache.is_seen(job["url"]):
                continue
            self.cache.mark_seen(job["url"])
            deduped.append(job)
            
        return deduped

    def _parse_jobspy_df(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Standardizes JobSpy DataFrame records into normalized structures."""
        df = df.fillna("")
        records = df.to_dict(orient="records")
        for rec in records:
            for k, v in rec.items():
                if pd.isna(v) or str(v) == "NaT":
                    rec[k] = ""
                elif isinstance(v, (datetime, pd.Timestamp)):
                    rec[k] = v.isoformat()
        return records

    def _is_within_24_hours(self, date_str: str, snippet: str = "") -> bool:
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
