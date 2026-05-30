"""JobSpy search engine implementation."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class JobSpySearcher:
    """Searcher that wraps python-jobspy for multiple job platforms."""

    SUPPORTED_COUNTRIES = {
        "argentina": "Argentina",
        "australia": "Australia",
        "austria": "Austria",
        "bahrain": "Bahrain",
        "belgium": "Belgium",
        "brazil": "Brazil",
        "canada": "Canada",
        "chile": "Chile",
        "china": "China",
        "colombia": "Colombia",
        "costa rica": "Costa Rica",
        "czech republic": "Czech Republic",
        "denmark": "Denmark",
        "ecuador": "Ecuador",
        "egypt": "Egypt",
        "finland": "Finland",
        "france": "France",
        "germany": "Germany",
        "greece": "Greece",
        "hong kong": "Hong Kong",
        "hungary": "Hungary",
        "india": "India",
        "indonesia": "Indonesia",
        "ireland": "Ireland",
        "israel": "Israel",
        "italy": "Italy",
        "japan": "Japan",
        "kuwait": "Kuwait",
        "luxembourg": "Luxembourg",
        "malaysia": "Malaysia",
        "mexico": "Mexico",
        "morocco": "Morocco",
        "netherlands": "Netherlands",
        "new zealand": "New Zealand",
        "nigeria": "Nigeria",
        "norway": "Norway",
        "oman": "Oman",
        "pakistan": "Pakistan",
        "panama": "Panama",
        "peru": "Peru",
        "philippines": "Philippines",
        "poland": "Poland",
        "portugal": "Portugal",
        "qatar": "Qatar",
        "romania": "Romania",
        "saudi arabia": "Saudi Arabia",
        "singapore": "Singapore",
        "south africa": "South Africa",
        "south korea": "South Korea",
        "spain": "Spain",
        "sweden": "Sweden",
        "switzerland": "Switzerland",
        "taiwan": "Taiwan",
        "thailand": "Thailand",
        "turkey": "Turkey",
        "ukraine": "Ukraine",
        "united arab emirates": "United Arab Emirates",
        "uae": "United Arab Emirates",
        "uk": "UK",
        "united kingdom": "UK",
        "usa": "USA",
        "us": "USA",
        "united states": "USA",
        "uruguay": "Uruguay",
        "venezuela": "Venezuela",
        "vietnam": "Vietnam",
    }

    JOB_TYPE_MAP = {
        "full-time": "fulltime",
        "fulltime": "fulltime",
        "part-time": "parttime",
        "parttime": "parttime",
        "internship": "internship",
        "intern": "internship",
        "contract": "contract",
        "contractor": "contract",
    }

    COUNTRY_ALIASES = {
        "egypt": ["egypt", "eg", "cairo", "giza", "alexandria"],
        "usa": ["usa", "us", "united states", "america"],
        "us": ["usa", "us", "united states", "america"],
        "united kingdom": ["uk", "gb", "united kingdom", "london", "great britain"],
        "uk": ["uk", "gb", "united kingdom", "london", "great britain"],
        "germany": ["germany", "de", "deutschland", "berlin", "munich"],
        "france": ["france", "fr", "paris"],
        "canada": ["canada", "ca", "toronto", "vancouver", "montreal"],
        "australia": ["australia", "au", "sydney", "melbourne"],
        "saudi arabia": ["saudi arabia", "sa", "riyadh", "jeddah"],
        "uae": ["uae", "ae", "united arab emirates", "dubai", "abu dhabi"],
        "united arab emirates": ["uae", "ae", "united arab emirates", "dubai", "abu dhabi"],
        "qatar": ["qatar", "qa", "doha"],
        "kuwait": ["kuwait", "kw"],
        "bahrain": ["bahrain", "bh", "manama"],
        "oman": ["oman", "om", "muscat"],
    }

    def __init__(self) -> None:
        pass

    def _scrape_site_sync(
        self,
        site: str,
        search_term: str,
        location: str,
        results_wanted: int,
        hours_old: Optional[int],
        is_remote: bool,
        country_indeed: str,
        job_type: Optional[str],
        easy_apply: Optional[bool],
        linkedin_fetch_description: bool,
        linkedin_company_ids: Optional[list[int]],
        google_search_term: Optional[str],
        distance: Optional[int],
        proxies: Optional[list[str]],
        enforce_annual_salary: Optional[bool],
        user_agent: Optional[str],
        ca_cert: Optional[str],
        description_format: str,
    ) -> list[dict]:
        from datetime import datetime

        from jobspy import scrape_jobs
        import pandas as pd

        params = {
            "site_name": [site],
            "search_term": search_term,
            "results_wanted": results_wanted,
            "description_format": description_format,
        }

        if distance is not None:
            params["distance"] = distance
        if proxies:
            params["proxies"] = proxies
        if enforce_annual_salary is not None:
            params["enforce_annual_salary"] = enforce_annual_salary
        if user_agent:
            params["user_agent"] = user_agent
        if ca_cert:
            params["ca_cert"] = ca_cert

        if site in ("indeed", "glassdoor"):
            params["country_indeed"] = country_indeed
            resolved_indeed_loc = location
            indeed_is_remote = is_remote

            if country_indeed in ("Egypt", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman"):
                if location == "remote":
                    resolved_indeed_loc = country_indeed
                    indeed_is_remote = False
                elif not location:
                    resolved_indeed_loc = country_indeed

            if resolved_indeed_loc:
                params["location"] = resolved_indeed_loc

            if easy_apply is True:
                params["easy_apply"] = True
            elif job_type or indeed_is_remote:
                if job_type:
                    params["job_type"] = job_type
                if indeed_is_remote:
                    params["is_remote"] = True
            else:
                if hours_old is not None:
                    params["hours_old"] = hours_old

        elif site == "linkedin":
            resolved_linkedin_loc = location
            if location == "remote" and country_indeed != "worldwide":
                resolved_linkedin_loc = country_indeed
            elif not location and country_indeed != "worldwide":
                resolved_linkedin_loc = country_indeed

            if resolved_linkedin_loc:
                params["location"] = resolved_linkedin_loc

            if easy_apply is True:
                params["easy_apply"] = True
            else:
                if hours_old is not None:
                    params["hours_old"] = hours_old
            if is_remote:
                params["is_remote"] = True
            if job_type:
                params["job_type"] = job_type
            if linkedin_fetch_description:
                params["linkedin_fetch_description"] = True
            if linkedin_company_ids:
                params["linkedin_company_ids"] = linkedin_company_ids

        elif site == "google":
            if google_search_term:
                params["google_search_term"] = google_search_term
            else:
                loc_suffix = f" near {location}" if location else ""
                age_suffix = " since yesterday" if (hours_old and hours_old <= 24) else ""
                params["google_search_term"] = f"{search_term} jobs{loc_suffix}{age_suffix}"

        elif site == "zip_recruiter":
            if location:
                params["location"] = location

        elif site == "bayt":
            pass

        else:
            if location:
                params["location"] = location
            if hours_old is not None:
                params["hours_old"] = hours_old
            if is_remote:
                params["is_remote"] = True
            if job_type:
                params["job_type"] = job_type

        try:
            logger.info(
                f"JobSpy single scrape started for site='{site}', params={ {k: v for k, v in params.items() if k != 'proxies'} }"
            )
            df = scrape_jobs(**params)
            if df is None or df.empty:
                logger.info(f"JobSpy site '{site}' returned no results.")
                return []

            df = df.fillna("")
            records = df.to_dict(orient="records")

            for rec in records:
                for k, v in rec.items():
                    if pd.isna(v) or str(v) == "NaT":
                        rec[k] = ""
                    elif isinstance(v, (datetime, pd.Timestamp)):
                        rec[k] = v.isoformat()

            logger.info(f"JobSpy site '{site}' completed successfully. Got {len(records)} jobs.")
            return records

        except Exception as e:
            logger.error(f"JobSpy scraping failed for site '{site}': {e}", exc_info=True)
            return []

    async def search(
        self,
        keywords: list[str],
        site_name: list[str],
        location: str = "remote",
        results_wanted: int = 50,
        hours_old: Optional[int] = 72,
        is_remote: bool = True,
        countries: list[str] = None,
        strict_country: bool = False,
        job_type: Optional[str] = None,
        easy_apply: Optional[bool] = None,
        linkedin_fetch_description: bool = False,
        linkedin_company_ids: Optional[list[int]] = None,
        google_search_term: Optional[str] = None,
        distance: Optional[int] = 50,
        proxies: Optional[list[str]] = None,
        enforce_annual_salary: Optional[bool] = None,
        user_agent: Optional[str] = None,
        ca_cert: Optional[str] = None,
        description_format: str = "markdown",
    ) -> list[dict]:
        import pandas as pd
        from datetime import datetime

        search_term = " OR ".join(keywords)
        country_indeed = "worldwide"
        if countries:
            primary_country = countries[0].lower().strip()
            country_indeed = self.SUPPORTED_COUNTRIES.get(primary_country, primary_country.title())

        mapped_job_type = None
        if job_type:
            mapped_job_type = self.JOB_TYPE_MAP.get(job_type.lower().strip(), job_type)

        loop = asyncio.get_event_loop()

        async def _scrape_async(site: str) -> list[dict]:
            return await loop.run_in_executor(
                None,
                self._scrape_site_sync,
                site,
                search_term,
                location,
                results_wanted,
                hours_old,
                is_remote,
                country_indeed,
                mapped_job_type,
                easy_apply,
                linkedin_fetch_description,
                linkedin_company_ids,
                google_search_term,
                distance,
                proxies,
                enforce_annual_salary,
                user_agent,
                ca_cert,
                description_format,
            )

        logger.info(f"Launching parallel JobSpy scrapers for sites: {site_name}")
        tasks = [_scrape_async(site) for site in site_name]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        combined_jobs = []
        for site, res in zip(site_name, results_nested):
            if isinstance(res, Exception):
                logger.error(f"Concurrent scraper task for site '{site}' raised exception: {res}")
                continue
            combined_jobs.extend(res)

        if strict_country and countries:
            logger.info(f"Applying strict country filtering for: {countries}")
            filtered_jobs = []
            match_terms = []
            for c in countries:
                norm_c = c.lower().strip()
                aliases = self.COUNTRY_ALIASES.get(norm_c)
                if aliases:
                    match_terms.extend(aliases)
                else:
                    match_terms.append(norm_c)

            for job in combined_jobs:
                loc = str(job.get("location", "")).lower()
                company_addr = str(job.get("company_addresses", "")).lower()
                if any(term in loc for term in match_terms) or any(term in company_addr for term in match_terms):
                    filtered_jobs.append(job)

            logger.info(
                f"Strict country filter completed. {len(combined_jobs)} -> {len(filtered_jobs)} jobs."
            )
            combined_jobs = filtered_jobs

        logger.info(f"JobSpy parallel scrape completed. Combined total: {len(combined_jobs)} raw jobs.")
        return combined_jobs


__all__ = ["JobSpySearcher"]
