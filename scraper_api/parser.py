"""
Job Result Parser
Takes raw DuckDuckGo results (title, href, body) and extracts
structured job fields: title, company, URL, description, salary, location.
Uses pattern matching + heuristics — no extra HTTP requests needed.
"""

import re
import hashlib
import logging
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class JobResultParser:

    # URL patterns that identify each job board
    SOURCE_PATTERNS = [
        (r"linkedin\.com/jobs",          "linkedin"),
        (r"weworkremotely\.com",         "weworkremotely"),
        (r"remotive\.com",               "remotive"),
        (r"indeed\.com",                 "indeed"),
        (r"wellfound\.com|angel\.co",    "wellfound"),
        (r"greenhouse\.io",              "greenhouse"),
        (r"lever\.co",                   "lever"),
        (r"workable\.com",               "workable"),
        (r"ashbyhq\.com",                "ashby"),
        (r"jobicy\.com",                 "jobicy"),
        (r"simplyhired\.com",            "simplyhired"),
        (r"glassdoor\.com",              "glassdoor"),
        (r"jobs\.github\.com",           "github-jobs"),
        (r"stackoverflow\.com/jobs",     "stackoverflow"),
    ]

    # Salary extraction patterns
    SALARY_PATTERNS = [
        r'\$[\d,]+(?:k|K)?(?:\s*[-–]\s*\$[\d,]+(?:k|K)?)?(?:\s*/\s*(?:yr|year|mo|month|hr|hour))?',
        r'[\d,]+(?:k|K)\s*[-–]\s*[\d,]+(?:k|K)',
        r'(?:USD|EUR|GBP)\s*[\d,]+(?:\s*[-–]\s*[\d,]+)?',
        r'up to \$[\d,]+',
        r'salary[:\s]+[\$€£]?[\d,]+',
    ]

    # Company extraction patterns from page titles
    COMPANY_FROM_TITLE = [
        r'^(.+?)\s+(?:is\s+)?hiring',
        r'^(.+?)\s+[-|–]\s+(?:jobs?|careers?)',
        r'(?:at|@)\s+(.+?)(?:\s+[-|]|\s*$)',
        r'(?:job|position|role)\s+at\s+(.+?)(?:\s+[-|]|\s*$)',
    ]

    # Patterns to detect non-job pages (forums, ad servers, blog posts, etc.)
    NOISE_PATTERNS = [
        r'reddit\.com', r'quora\.com', r'stackexchange\.com',
        r'medium\.com', r'dev\.to', r'youtube\.com',
        r'twitter\.com', r'facebook\.com', r'instagram\.com',
        r'wikipedia\.org', r'coursera\.org', r'udemy\.com',
        r'bing\.com/aclick', r'doubleclick\.net', r'googleadservices\.com',
        r'yandex\.ru/clck', r'yandex\.com/clck', r'adservice\.google',
        r'ad\.doubleclick', r'clickserve', r'adform\.net',
    ]

    # Title cleanup patterns
    JOB_TITLE_CLEANERS = [
        (r'\s*[-|–]\s*(remote|full.time|part.time|contract).*$', '', re.I),
        (r'\s+at\s+.+$', '', re.I),
        (r'\s*\|\s*.+$', ''),
        (r'\s*-\s*.+$', ''),
        (r'\(.*?\)', ''),
        (r'\s{2,}', ' '),
    ]

    def parse_many(self, raw_results: list[dict]) -> list[dict]:
        """Parse a list of raw DDG results into structured job dicts."""
        parsed  = []
        seen_ids = set()

        for raw in raw_results:
            try:
                job = self._parse_one(raw)
                if job is None:
                    continue
                if job["id"] in seen_ids:
                    continue
                seen_ids.add(job["id"])
                parsed.append(job)
            except Exception as e:
                logger.debug(f"Parse error: {e} — {raw.get('href','')[:60]}")

        logger.info(f"Parsed {len(parsed)} valid jobs from {len(raw_results)} raw results")
        return parsed

    def _parse_one(self, raw: dict) -> dict | None:
        url   = raw.get("href", "")
        title = raw.get("title", "")
        body  = raw.get("body", "")

        if not url or not title:
            return None

        # Filter out noise domains
        for noise in self.NOISE_PATTERNS:
            if re.search(noise, url, re.I):
                return None

        # Must look like a job page
        if not self._is_likely_job_url(url):
            return None

        # Must be a specific job posting, not a landing page or index page
        if not self._is_specific_job_url(url):
            return None

        # Ensure URL matches the searched job site (if specified and not multi-site)
        dork_site = raw.get("_dork_site", "")
        if dork_site and dork_site != "multi-site":
            expected_domain = dork_site.split("/")[0].lower()
            url_lower = url.lower()
            if expected_domain == "wellfound.com" and "angel.co" in url_lower:
                pass
            elif expected_domain not in url_lower:
                logger.info(f"Rejected URL {url} as it does not match expected dork site {dork_site}")
                return None

        source   = self._detect_source(url)
        job_title = self._extract_job_title(title, body)
        company   = self._extract_company(title, body, url)
        salary    = self._extract_salary(body + " " + title)
        location  = self._extract_location(body + " " + title)
        posted_at = self._extract_posted_at(raw, title, body)
        score     = self._score_result(title, body, raw)

        # Build stable ID from URL
        job_id = hashlib.md5(url.encode()).hexdigest()

        return {
            "id":          job_id,
            "title":       job_title,
            "company":     company,
            "url":         url,
            "description": body[:800].strip(),
            "location":    location,
            "salary":      salary,
            "source":      source,
            "dork_query":  raw.get("_dork_query", ""),
            "posted_at":   posted_at,
            "score":       score,
        }

    def _is_likely_job_url(self, url: str) -> bool:
        job_signals = [
            "job", "career", "position", "hire", "opening",
            "vacancy", "role", "apply", "greenhouse", "lever",
            "workable", "ashby", "bamboo",
        ]
        url_lower = url.lower()
        return any(s in url_lower for s in job_signals)

    def _is_specific_job_url(self, url: str) -> bool:
        """
        Ensure we filter out search, index, collection, and company job-list pages.
        Only allow URLs that point to a single, specific job posting.
        """
        url_lower = url.lower()
        parsed = urlparse(url)
        path_segments = [seg for seg in parsed.path.split("/") if seg]

        # LinkedIn: must be a specific view page
        if "linkedin.com" in url_lower:
            return "/jobs/view" in parsed.path or "viewjob" in url_lower

        # Indeed: must be a viewjob or clk page
        if "indeed.com" in url_lower:
            return "/viewjob" in parsed.path or "/rc/clk" in parsed.path

        # Lever: jobs.lever.co/company/job_id (path has >= 2 segments)
        if "lever.co" in url_lower:
            return len(path_segments) >= 2

        # Greenhouse: boards.greenhouse.io/company/jobs/job_id (path has >= 3 segments and contains jobs)
        if "greenhouse.io" in url_lower:
            return "/jobs/" in parsed.path or len(path_segments) >= 3

        # Workable: apply.workable.com/company/j/job_id
        if "workable.com" in url_lower:
            return "/j/" in url_lower or "/jobs/" in url_lower or len(path_segments) >= 3

        # Ashby: jobs.ashbyhq.com/company/job-id
        if "ashbyhq.com" in url_lower:
            return len(path_segments) >= 2

        # Wellfound: wellfound.com/jobs/12345-job-title or angel.co/company/jobs/12345-job-title
        if "wellfound.com" in url_lower or "angel.co" in url_lower:
            return len(path_segments) >= 2

        return True

    def _detect_source(self, url: str) -> str:
        for pattern, name in self.SOURCE_PATTERNS:
            if re.search(pattern, url, re.I):
                return name
        # Fall back to hostname
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return "unknown"

    def _extract_job_title(self, title: str, body: str) -> str:
        """Clean page title down to just the job title."""
        cleaned = title.strip()
        for pattern, replacement, *flags in self.JOB_TITLE_CLEANERS:
            flag = flags[0] if flags else 0
            cleaned = re.sub(pattern, replacement, cleaned, flags=flag)
        cleaned = cleaned.strip()

        job_word = re.search(
            r'\b(engineer|developer|architect|devops|platform|sre|cloud|backend|frontend|full.stack)\b',
            cleaned,
            re.I,
        )
        body_title = re.search(
            r'((?:sr\.?|senior|mid|junior|lead|staff|principal)?\s*'
            r'(?:devops|platform|site reliability|cloud|backend|frontend|full.?stack|software|python|go|golang)'
            r'\s+(?:engineer|developer|architect|specialist))',
            body,
            re.I,
        )
        if not job_word and body_title:
            cleaned = body_title.group(1).strip()

        # If title looks too short after cleaning, try extracting from body
        if len(cleaned) < 5:
            m = re.search(r'(?:job title|position|role)[:\s]+([^\n.]+)', body, re.I)
            if m:
                cleaned = m.group(1).strip()

        return cleaned or title[:80]

    def _extract_company(self, title: str, body: str, url: str) -> str:
        """Try to extract company name from title, body, or URL."""
        # Try title patterns first
        for pattern in self.COMPANY_FROM_TITLE:
            m = re.search(pattern, title, re.I)
            if m:
                company = m.group(1).strip()
                if 3 < len(company) < 60:
                    return company

        # Try body
        for pattern in [
            r'company[:\s]+([A-Z][^\n,]{2,40})',
            r'(?:at|@|join)\s+([A-Z][A-Za-z0-9\s&.]{2,40}?)(?:\s+[-,|]|\s*$)',
        ]:
            m = re.search(pattern, body)
            if m:
                company = m.group(1).strip()
                if 3 < len(company) < 60:
                    return company

        # Fall back to subdomain or first path segment
        try:
            parsed = urlparse(url)
            path_company = parsed.path.strip("/").split("/")[0]
            if path_company and re.search(r'(lever|greenhouse|ashby|workable)', parsed.netloc, re.I):
                return path_company.replace("-", " ").title()
            parts  = parsed.netloc.replace("www.", "").split(".")
            return parts[0].replace("-", " ").title()
        except Exception:
            return "Unknown"

    def _extract_salary(self, text: str) -> str:
        """Extract salary range string if present."""
        for pattern in self.SALARY_PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(0).strip()
        return ""

    def _extract_location(self, text: str) -> str:
        """Extract location string."""
        # Remote first
        if re.search(r'\b(remote|work from home|fully remote|wfh)\b', text, re.I):
            return "Remote"
        # Explicit location tag
        m = re.search(r'location[:\s]+([^\n,|]{3,40})', text, re.I)
        if m:
            return m.group(1).strip()
        # City, Country / City, State patterns
        m = re.search(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?,\s*[A-Z]{2,})\b', text)
        if m:
            return m.group(1)
        return "Not specified"

    def _extract_posted_at(self, raw: dict, title: str, body: str) -> str:
        """Extract a posting timestamp from DDG metadata or snippet text."""
        for key in ["date", "published", "published_at", "posted_at", "timestamp"]:
            value = raw.get(key)
            parsed = self._parse_date_value(value)
            if parsed:
                return parsed

        text = f"{title} {body}"
        now = datetime.utcnow()

        relative_patterns = [
            (r'\b(?:posted|listed|published)?\s*(\d+)\s*(?:minute|minutes|min|mins)\s+ago\b', "minutes"),
            (r'\b(?:posted|listed|published)?\s*(\d+)\s*(?:hour|hours|hr|hrs)\s+ago\b', "hours"),
            (r'\b(?:posted|listed|published)?\s*(\d+)\s*(?:day|days)\s+ago\b', "days"),
        ]
        for pattern, unit in relative_patterns:
            match = re.search(pattern, text, re.I)
            if not match:
                continue
            amount = int(match.group(1))
            if unit == "minutes":
                return (now - timedelta(minutes=amount)).isoformat()
            if unit == "hours":
                return (now - timedelta(hours=amount)).isoformat()
            if unit == "days":
                return (now - timedelta(days=amount)).isoformat()

        if re.search(r'\b(just posted|posted today|today)\b', text, re.I):
            return now.isoformat()
        if re.search(r'\b(yesterday)\b', text, re.I):
            return (now - timedelta(days=1)).isoformat()

        for pattern in [
            r'\b(20\d{2}-\d{2}-\d{2})(?:[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?)?\b',
            r'\b([A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2})\b',
            r'\b(\d{1,2}\s+[A-Z][a-z]{2,8}\s+20\d{2})\b',
        ]:
            match = re.search(pattern, text)
            if match:
                parsed = self._parse_date_value(match.group(1))
                if parsed:
                    return parsed

        return ""

    def _parse_date_value(self, value) -> str:
        if value is None or value == "":
            return ""

        if isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(value).isoformat()
            except Exception:
                return ""

        text = str(value).strip()
        if not text:
            return ""

        if text.isdigit():
            try:
                timestamp = int(text)
                if timestamp > 10_000_000_000:
                    timestamp = timestamp / 1000
                return datetime.utcfromtimestamp(timestamp).isoformat()
            except Exception:
                return ""

        try:
            normalized = text.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo:
                parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
            return parsed.isoformat()
        except Exception:
            pass

        try:
            parsed = parsedate_to_datetime(text)
            if parsed.tzinfo:
                parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
            return parsed.isoformat()
        except Exception:
            pass

        for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(text, fmt).isoformat()
            except Exception:
                continue

        return ""

    def _score_result(self, title: str, body: str, raw: dict) -> float:
        """
        Score a result 0-10 based on signals that suggest it's a real,
        relevant, recent job posting.
        """
        score = 5.0
        text  = (title + " " + body).lower()

        # Positive signals
        if re.search(r'\b(apply|application|requirements|qualifications)\b', text):
            score += 1.0
        if re.search(r'\b(salary|compensation|benefits|equity)\b', text):
            score += 0.5
        if re.search(r'\b(remote|full.time|contract|part.time)\b', text):
            score += 0.5
        if re.search(r'\b(devops|kubernetes|docker|terraform|aws|python|golang)\b', text):
            score += 1.0
        if re.search(r'\b(senior|lead|staff|principal)\b', text):
            score += 0.3
        if self._is_likely_job_url(raw.get("href", "")):
            score += 0.5

        # Negative signals
        if re.search(r'\b(mlm|pyramid|unlimited earning|be your own boss)\b', text):
            score -= 4.0
        if re.search(r'\b(no experience|earn from home|make money)\b', text):
            score -= 3.0
        if re.search(r'\b(sponsored|advertisement|ad by)\b', text):
            score -= 2.0

        return max(0.0, min(10.0, round(score, 1)))
