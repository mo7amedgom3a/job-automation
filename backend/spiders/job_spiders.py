"""
Concrete job-board spiders.

Each class is ~20-40 lines:  it only declares its SiteConfig and implements
extract_jobs().  All infrastructure (sessions, pagination, dedup, retries,
logging) is handled by BaseJobSpider.

────────────────────────────────────────────────────────────────────────────
  To add a new job board:
    1. Create a new SiteConfig in config/settings.py.
    2. Add a new class here inheriting from BaseJobSpider.
    3. Set site_config = <your SiteConfig>.
    4. Implement extract_jobs(response) to yield job dicts.
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from typing import AsyncGenerator
from scrapling.spiders import Response, Request

from config.settings import SITES
from spiders.base import BaseJobSpider


# ── Helper to look up a SiteConfig by name ───────────────────────────────────
def _cfg(name: str):
    for s in SITES:
        if s.name == name:
            return s
    raise ValueError(f"No SiteConfig named '{name}'")


# ─────────────────────────────────────────────────────────────────────────────
# 1.  Remote OK  (plain HTML, no JS needed)
# ─────────────────────────────────────────────────────────────────────────────

class RemoteOKSpider(BaseJobSpider):
    site_config = _cfg("remoteok")

    async def extract_jobs(self, response: Response):
        # RemoteOK renders a <table> of <tr class="job"> rows
        for row in response.css("tr.job"):
            title    = row.css("h2[itemprop='title']::text").get("").strip()
            company  = row.css("h3[itemprop='name']::text").get("").strip()
            location = row.css("div.location::text").get("Remote").strip()
            url      = row.css("a[itemprop='url']::attr(href)").get("").strip()
            tags     = row.css("a.tag::text").getall()
            salary   = row.css("div.salary::text").get("").strip()

            if title and url:
                if url.startswith("/"):
                    url = f"https://remoteok.com{url}"
                yield {
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      url,
                    "tags":     tags,
                    "salary":   salary,
                }


# ─────────────────────────────────────────────────────────────────────────────
# 2.  We Work Remotely
# ─────────────────────────────────────────────────────────────────────────────

class WeWorkRemotelySpider(BaseJobSpider):
    site_config = _cfg("weworkremotely")

    async def extract_jobs(self, response: Response):
        for card in response.css("a[href*='/remote-jobs/']"):
            title = card.css(".new-listing__header__title__text::text").get("").strip()
            company = card.css(".new-listing__company-name::text").get("").strip()
            location = card.css(".new-listing__company-headquarters::text").get("Remote").strip()
            href = card.attrib.get("href", "").strip()

            # Clean up potential duplicate spaces/newlines in parsed text
            company = " ".join(company.split())
            location = " ".join(location.split())

            if title and href:
                url = f"https://weworkremotely.com{href}" if href.startswith("/") else href
                yield {
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      url,
                }


# ─────────────────────────────────────────────────────────────────────────────
# 3.  Jobicy
# ─────────────────────────────────────────────────────────────────────────────

class JobicySpider(BaseJobSpider):
    site_config = _cfg("jobicy")

    async def extract_jobs(self, response: Response):
        # Defensive check: if the response is JSON (from the API), parse it directly
        try:
            import json
            data = json.loads(response.body)
            if isinstance(data, dict) and "jobs" in data:
                for job in data.get("jobs", []):
                    title = job.get("jobTitle", "").strip()
                    company = job.get("companyName", "").strip()
                    location = job.get("jobGeo", "Remote").strip()
                    url = job.get("url", "").strip()
                    tags = job.get("jobIndustry", []) + job.get("jobType", [])

                    if title and url:
                        yield {
                            "title":    title,
                            "company":  company,
                            "location": location,
                            "url":      url,
                            "tags":     tags,
                            "salary":   "",
                        }
                return
        except Exception:
            pass

        # Fallback to HTML CSS parsing if API ever fails or changes back to HTML page
        for card in response.css("article.job-card, li.job-item, div.job-post"):
            title    = card.css(".job-title::text, h2 a::text").get("").strip()
            company  = card.css(".company-name::text, .employer::text").get("").strip()
            location = card.css(".job-location::text, .location::text").get("Remote").strip()
            url      = card.css("a.job-link::attr(href), h2 a::attr(href)").get("").strip()
            tags     = card.css(".tag::text, .skill::text").getall()
            salary   = card.css(".salary::text").get("").strip()

            if title and url:
                if url.startswith("/"):
                    url = f"https://jobicy.com{url}"
                yield {
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      url,
                    "tags":     tags,
                    "salary":   salary,
                }


# ─────────────────────────────────────────────────────────────────────────────
# 4.  Remotive  (JS-rendered, uses DynamicFetcher)
# ─────────────────────────────────────────────────────────────────────────────

class RemotiveSpider(BaseJobSpider):
    site_config = _cfg("remotive")

    async def extract_jobs(self, response: Response):
        # Defensive check: if the response is JSON (from the API), parse it directly
        try:
            import json
            data = json.loads(response.body)
            if isinstance(data, dict) and "jobs" in data:
                for job in data.get("jobs", []):
                    title = job.get("title", "").strip()
                    company = job.get("company_name", "").strip()
                    location = job.get("candidate_required_location", "Remote").strip()
                    url = job.get("url", "").strip()
                    tags = job.get("tags", [])
                    salary = job.get("salary", "").strip()

                    if title and url:
                        yield {
                            "title":    title,
                            "company":  company,
                            "location": location,
                            "url":      url,
                            "tags":     tags,
                            "salary":   salary,
                        }
                return
        except Exception:
            pass

        # Fallback to HTML CSS parsing if API ever fails or changes back to HTML page
        for card in response.css("li.job-card, div[class*='JobCard']"):
            title    = card.css("h3, .job-title::text").get("").strip()
            company  = card.css(".company-name::text, .companyName::text").get("").strip()
            location = card.css(".job-location::text, [class*='location']::text").get("Remote").strip()
            url      = card.css("a::attr(href)").get("").strip()
            tags     = card.css(".tag::text, [class*='tag']::text").getall()
            salary   = card.css("[class*='salary']::text").get("").strip()

            if title and url:
                if url.startswith("/"):
                    url = f"https://remotive.com{url}"
                yield {
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      url,
                    "tags":     tags,
                    "salary":   salary,
                }


# ─────────────────────────────────────────────────────────────────────────────
# 5.  Himalayas  (StealthyFetcher — light bot protection)
# ─────────────────────────────────────────────────────────────────────────────

class HimalayasSpider(BaseJobSpider):
    site_config = _cfg("himalayas")

    async def extract_jobs(self, response: Response):
        # Defensive check: if the response is JSON (from the API), parse it directly
        try:
            import json
            data = json.loads(response.body)
            if isinstance(data, dict) and "jobs" in data:
                for job in data.get("jobs", []):
                    title = job.get("title", "").strip()
                    company = job.get("companyName", "").strip()
                    url = job.get("applicationLink", "").strip()
                    
                    # Construct location
                    locations = job.get("locationRestrictions", [])
                    location = ", ".join(locations) if locations else "Remote"
                    
                    # Construct tags
                    tags = job.get("categories", [])
                    if job.get("employmentType"):
                        tags.append(job.get("employmentType"))
                    
                    # Construct salary
                    min_sal = job.get("minSalary")
                    max_sal = job.get("maxSalary")
                    currency = job.get("currency", "USD")
                    salary = ""
                    if min_sal and max_sal:
                        salary = f"{min_sal} - {max_sal} {currency}"
                    elif min_sal:
                        salary = f"From {min_sal} {currency}"
                    elif max_sal:
                        salary = f"Up to {max_sal} {currency}"

                    if title and url:
                        yield {
                            "title":    title,
                            "company":  company,
                            "location": location,
                            "url":      url,
                            "tags":     tags,
                            "salary":   salary,
                        }
                return
        except Exception:
            pass

        # Fallback to HTML CSS parsing if API ever fails or changes back to HTML page
        for card in response.css("li[class*='job'], div[class*='JobCard'], article"):
            title    = card.css("h2 a::text, h3 a::text, [class*='title']::text").get("").strip()
            company  = card.css("[class*='company']::text, [class*='employer']::text").get("").strip()
            location = card.css("[class*='location']::text").get("Remote").strip()
            url      = card.css("a[href*='/jobs/']::attr(href)").get("").strip()
            tags     = card.css("[class*='skill']::text, [class*='tag']::text").getall()
            salary   = card.css("[class*='salary']::text, [class*='compensation']::text").get("").strip()

            if title and url:
                if url.startswith("/"):
                    url = f"https://himalayas.app{url}"
                yield {
                    "title":    title,
                    "company":  company,
                    "location": location,
                    "url":      url,
                    "tags":     tags,
                    "salary":   salary,
                }


# ─────────────────────────────────────────────────────────────────────────────
# 6.  TrueUp
# ─────────────────────────────────────────────────────────────────────────────

class TrueUpSpider(BaseJobSpider):
    site_config = _cfg("trueup")

    async def extract_jobs(self, response: Response) -> AsyncGenerator[dict, None]:
        for card in response.css("div.p-4"):
            title_text = card.css("a.text-foreground.text-lg::text").get("").strip()
            if not title_text:
                title_text = card.css("button.text-foreground.text-lg::text").get("").strip()
            if not title_text:
                title_text = card.css("div.mb-1.font-bold a::text").get("").strip()
            if not title_text:
                title_text = card.css("div.mb-1.font-bold button::text").get("").strip()

            # Clean title to take the first non-empty line (extracts exact title and ignores badged categories)
            lines = [line.strip() for line in title_text.split('\n') if line.strip()]
            title = lines[0] if lines else ""
            title = " ".join(title.split())

            if not title:
                continue

            url = card.css("a.text-foreground.text-lg::attr(href)").get("").strip()
            if not url:
                url = card.css("div.mb-1.font-bold a::attr(href)").get("").strip()
            if not url:
                url = card.css("a[href$='/jobs']::attr(href)").get("").strip()
            if not url:
                url = card.css("a[href^='/co/']::attr(href)").get("").strip()
            if not url:
                url = "/jobs"

            if url.startswith("/"):
                url = f"https://www.trueup.io{url}"

            company = card.css("a.text-base.font-medium::text").get("").strip()
            if not company:
                company = card.css("a[href^='/co/']::text").get("").strip()

            company = " ".join(company.split())

            location = card.css("div.line-clamp-3::text").get("Remote").strip()
            location = " ".join(location.split())
            if not location:
                location = "Remote"

            salary = ""
            flex_col = card.css("div.flex.flex-col.gap-y-2")
            if flex_col:
                salary = flex_col.css("div.text-sm::text").get("").strip()
                salary = " ".join(salary.split())

            tags = card.css("span.font-mono::text").getall()
            tags = [t.strip() for t in tags if t.strip()]
            print(f"Extracted job: title='{title}', company='{company}', location='{location}', url='{url}', tags={tags}, salary='{salary}'")
            yield {
                "title":    title,
                "company":  company,
                "location": location,
                "url":      url,
                "tags":     tags,
                "salary":   salary,
            }



# ─────────────────────────────────────────────────────────────────────────────
# 7.  LinkedIn
# ─────────────────────────────────────────────────────────────────────────────

class LinkedInSpider(BaseJobSpider):
    site_config = _cfg("linkedin")

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        import os
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        # Parse query params from the configured start URL
        start_url = self.site_config.start_urls[0]
        parsed = urlparse(start_url)
        params = parse_qs(parsed.query)

        # Get first element of query parameters list, or default
        keywords = os.getenv("LINKEDIN_KEYWORDS", params.get("keywords", ["Software Engineer"])[0])
        location = os.getenv("LINKEDIN_LOCATION", params.get("location", ["Cairo"])[0])
        geo_id = os.getenv("LINKEDIN_GEO_ID", params.get("geoId", ["101131993"])[0])
        distance = os.getenv("LINKEDIN_DISTANCE", params.get("distance", ["25"])[0])
        tpr = os.getenv("LINKEDIN_TPR", params.get("f_TPR", ["r86400"])[0])
        f_wt = params.get("f_WT", [])

        # Build parameters dictionary
        query_dict = {
            "keywords": keywords,
            "location": location,
            "geoId": geo_id,
            "distance": distance,
            "f_TPR": tpr
        }
        if f_wt:
            query_dict["f_WT"] = f_wt[0]

        # Carry over other potential query parameters from the config URL
        for k, v in params.items():
            if k not in query_dict:
                query_dict[k] = v[0]

        # Reconstruct search URL
        new_query = urlencode(query_dict)
        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        self.logger.info("Generated dynamic LinkedIn Search URL: %s", url)

        sid = self._default_sid()
        cfg = self.site_config
        kwargs = cfg.extra_fetch_kwargs or {}
        yield Request(url, callback=self.parse, sid=sid, **kwargs)

    async def extract_jobs(self, response: Response) -> AsyncGenerator[dict, None]:
        for card in response.css("div.job-search-card"):
            title = card.css("h3.base-search-card__title::text").get("").strip()
            title = " ".join(title.split())

            url = card.css("a.base-card__full-link::attr(href)").get("").strip()

            if not title or not url:
                continue

            company = card.css("h4.base-search-card__subtitle a::text").get("").strip()
            if not company:
                company = card.css("h4.base-search-card__subtitle::text").get("").strip()
            company = " ".join(company.split())

            location = card.css("span.job-search-card__location::text").get("Remote").strip()
            location = " ".join(location.split())
            if not location:
                location = "Remote"

            # Check if there is dynamic salary under the custom class
            salary = ""
            salary_el = card.css("span.job-search-card__salary-info")
            if salary_el:
                salary = salary_el.css("::text").get("").strip()
            salary = " ".join(salary.split())

            # Construct tags including listdate if present
            tags = []
            listdate = card.css("time::attr(datetime)").get("").strip()
            if listdate:
                tags.append(f"Posted {listdate}")

            yield {
                "title":    title,
                "company":  company,
                "location": location,
                "url":      url,
                "tags":     tags,
                "salary":   salary,
            }


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Indeed
# ─────────────────────────────────────────────────────────────────────────────

class IndeedSpider(BaseJobSpider):
    site_config = _cfg("indeed")

    async def start_requests(self) -> AsyncGenerator[Request, None]:
        import os
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        # Parse query params from the configured start URL
        start_url = self.site_config.start_urls[0]
        parsed = urlparse(start_url)
        params = parse_qs(parsed.query)

        # Get first element of query parameters list, or default
        query = os.getenv("INDEED_QUERY", params.get("q", ['"software engineer" OR DevOps OR backend OR AWS OR terraform OR python OR Golang'])[0])
        location = os.getenv("INDEED_LOCATION", params.get("l", [""])[0])
        fromage = os.getenv("INDEED_FROMAGE", params.get("fromage", ["3"])[0])
        limit = os.getenv("INDEED_LIMIT", params.get("limit", [""])[0])

        query_dict = {
            "q": query,
            "l": location,
            "fromage": fromage,
        }
        if limit:
            query_dict["limit"] = limit

        # Carry over other potential query parameters from the config URL
        for k, v in params.items():
            if k not in query_dict:
                query_dict[k] = v[0]

        # Reconstruct search URL
        new_query = urlencode(query_dict, safe="%")
        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        self.logger.info("Generated dynamic Indeed Search URL: %s", url)

        sid = self._default_sid()
        cfg = self.site_config
        kwargs = cfg.extra_fetch_kwargs or {}
        yield Request(url, callback=self.parse, sid=sid, **kwargs)

    async def extract_jobs(self, response: Response) -> AsyncGenerator[dict, None]:
        # Parse the domain dynamically from the site config start URLs
        from urllib.parse import urlparse
        start_url = self.site_config.start_urls[0]
        parsed_domain = urlparse(start_url).netloc or "www.indeed.com"

        for card in response.css("div.cardOutline"):
            title = card.css("h3.jobTitle a span::text").get("").strip()
            if not title:
                title = card.css("h2.jobTitle a span::text").get("").strip()
            if not title:
                title = card.css("span[id^='jobTitle']::text").get("").strip()
            if not title:
                title = card.css("a.jcs-JobTitle span::text").get("").strip()
            title = " ".join(title.split())

            url = card.css("h3.jobTitle a::attr(href)").get("").strip()
            if not url:
                url = card.css("h2.jobTitle a::attr(href)").get("").strip()
            if not url:
                url = card.css("a.jcs-JobTitle::attr(href)").get("").strip()

            if not title or not url:
                continue

            if url.startswith("/"):
                url = f"https://{parsed_domain}{url}"

            company = card.css("span[data-testid='company-name']::text").get("").strip()
            if not company:
                company = card.css("span.companyName::text").get("").strip()
            company = " ".join(company.split())

            location = card.css("[data-testid='text-location']::text").get("").strip()
            if not location:
                location = card.css("[data-testid='text-location'] span::text").get("").strip()
            if not location:
                location = card.css("div.companyLocation::text").get("").strip()
            location = " ".join(location.split())
            if not location:
                location = "Remote"

            # Recursive description extraction to grab text within child tags
            desc_list = card.css("[data-testid='belowJobSnippet'] *::text").getall()
            description = " ".join(t.strip() for t in desc_list if t.strip())
            if not description:
                description = card.css("div.job-snippet::text").get("").strip()
            description = " ".join(description.split())

            # Salary extraction
            salary = card.css("div.salary-snippet-container::text").get("").strip()
            if not salary:
                salary = card.css("div.salarySnippet::text").get("").strip()
            if not salary:
                salary = card.css("[data-testid='attribute_snippet']::text").get("").strip()
            salary = " ".join(salary.split())

            # Tag extraction
            tags = card.css("div.jobMetaDataGroup span::text, ul.metadataContainer span::text").getall()
            tags = [t.strip() for t in tags if t.strip()]
            seen = set()
            tags = [t for t in tags if not (t in seen or seen.add(t))]

            yield {
                "title":        title,
                "company":      company,
                "location":     location,
                "url":          url,
                "description":  description,
                "tags":         tags,
                "salary":       salary,
            }


# ─── Country-Specific Spider Subclasses ───────────────────────────────────────

class LinkedInSASpider(LinkedInSpider):
    site_config = _cfg("linkedin_sa")

class LinkedInEGSpider(LinkedInSpider):
    site_config = _cfg("linkedin_eg")

class LinkedInAESpider(LinkedInSpider):
    site_config = _cfg("linkedin_ae")

class LinkedInBarcelonaSpider(LinkedInSpider):
    site_config = _cfg("linkedin_barcelona")

class LinkedInGermanySpider(LinkedInSpider):
    site_config = _cfg("linkedin_germany")

class LinkedInPolandSpider(LinkedInSpider):
    site_config = _cfg("linkedin_poland")

class LinkedInSpainSpider(LinkedInSpider):
    site_config = _cfg("linkedin_spain")

class LinkedInCanadaSpider(LinkedInSpider):
    site_config = _cfg("linkedin_canada")

class IndeedEGSpider(IndeedSpider):
    site_config = _cfg("indeed_eg")

class IndeedSASpider(IndeedSpider):
    site_config = _cfg("indeed_sa")

class IndeedAESpider(IndeedSpider):
    site_config = _cfg("indeed_ae")


# ─── Registry ─────────────────────────────────────────────────────────────────
# All active spider classes, keyed by their config name.

ALL_SPIDERS: dict[str, type[BaseJobSpider]] = {
    "remoteok":         RemoteOKSpider,
    "weworkremotely":   WeWorkRemotelySpider,
    "jobicy":           JobicySpider,
    "remotive":         RemotiveSpider,
    "himalayas":        HimalayasSpider,
    "trueup":           TrueUpSpider,
    "linkedin":         LinkedInSpider,
    "indeed":           IndeedSpider,
    "linkedin_sa":      LinkedInSASpider,
    "linkedin_eg":      LinkedInEGSpider,
    "linkedin_ae":      LinkedInAESpider,
    "linkedin_barcelona": LinkedInBarcelonaSpider,
    "linkedin_germany": LinkedInGermanySpider,
    "linkedin_poland":  LinkedInPolandSpider,
    "linkedin_spain":   LinkedInSpainSpider,
    "linkedin_canada":  LinkedInCanadaSpider,
    "indeed_eg":        IndeedEGSpider,
    "indeed_sa":        IndeedSASpider,
    "indeed_ae":        IndeedAESpider,
}



