"""
Dork Query Builder
Generates targeted Google Dork queries that hit multiple job boards
simultaneously, far more efficiently than scraping each site individually.

Dork syntax reference:
  site:domain.com          → only results from this domain
  intitle:"word"           → page title must contain word
  inurl:word               → URL must contain word
  "phrase"                 → exact phrase match
  -word                    → exclude word
  filetype:pdf             → specific file type (useful for job PDFs)
"""

from typing import Optional
from datetime import datetime, timedelta


class DorkQueryBuilder:

    # Job board site targets — tuned for each platform's URL/title structure
    SITE_CONFIGS = {
        "linkedin.com/jobs": {
            "url_pattern":   "site:linkedin.com/jobs/view",
            "title_signals": ["hiring", "job", "position"],
        },
        "weworkremotely.com": {
            "url_pattern":   "site:weworkremotely.com",
            "title_signals": ["remote job", "remote"],
        },
        "remotive.com": {
            "url_pattern":   "site:remotive.com/remote-jobs",
            "title_signals": [],
        },
        "indeed.com/jobs": {
            "url_pattern":   "site:indeed.com/viewjob",
            "title_signals": [],
        },
        "wellfound.com": {
            "url_pattern":   "site:wellfound.com/jobs",
            "title_signals": [],
        },
        "greenhouse.io": {
            "url_pattern":   "site:boards.greenhouse.io",
            "title_signals": [],
        },
        "lever.co": {
            "url_pattern":   "site:jobs.lever.co",
            "title_signals": [],
        },
        "workable.com": {
            "url_pattern":   "site:apply.workable.com",
            "title_signals": [],
        },
        "jobs.ashbyhq.com": {
            "url_pattern":   "site:jobs.ashbyhq.com",
            "title_signals": [],
        },
        "jobicy.com": {
            "url_pattern":   "site:jobicy.com",
            "title_signals": ["remote"],
        },
        "simplyhired.com": {
            "url_pattern":   "site:simplyhired.com/job",
            "title_signals": [],
        },
        "glassdoor.com": {
            "url_pattern":   "site:glassdoor.com/job-listing",
            "title_signals": [],
        },
    }

    # Keyword expansion map — expands a short skill into related search terms
    KEYWORD_EXPANSIONS = {
        "devops":       ["devops engineer", "platform engineer", "site reliability"],
        "kubernetes":   ["kubernetes", "k8s", "container orchestration"],
        "terraform":    ["terraform", "infrastructure as code", "IaC"],
        "docker":       ["docker", "containerization", "containers"],
        "aws":          ["aws", "amazon web services", "cloud engineer"],
        "python":       ["python developer", "python engineer", "backend python"],
        "fastapi":      ["fastapi", "python api", "rest api python"],
        "golang":       ["golang", "go developer", "go engineer"],
        "cicd":         ["ci/cd", "pipeline", "github actions", "jenkins"],
        "linux":        ["linux admin", "system administrator", "sre"],
        "ansible":      ["ansible", "configuration management", "automation"],
        "monitoring":   ["prometheus", "grafana", "observability", "monitoring"],
    }

    # Location modifiers for remote filtering
    LOCATION_MODIFIERS = {
        "remote":      ['"remote"'],
        "hybrid":      ['"hybrid"', '"hybrid remote"'],
        "onsite":      [],   # no modifier — return all
    }

    COUNTRY_TARGETS = {
        "egypt": {
            "terms": ['"Egypt"', '"Cairo"'],
            "locations": ["remote", "hybrid", "onsite"],
        },
        "mena": {
            "terms": ['"MENA"', '"Middle East"', '"Gulf"', '"UAE"', '"Saudi Arabia"', '"Egypt"'],
            "locations": ["remote"],
        },
        "eu": {
            "terms": ['"EU"', '"Europe"', '"European Union"', '"Germany"', '"Netherlands"', '"France"'],
            "locations": ["remote"],
        },
        "europe": {
            "terms": ['"Europe"', '"EU"', '"European Union"', '"Germany"', '"Netherlands"', '"France"'],
            "locations": ["remote"],
        },
        "usa": {
            "terms": ['"USA"', '"United States"', '"US"'],
            "locations": ["remote"],
        },
        "us": {
            "terms": ['"USA"', '"United States"', '"US"'],
            "locations": ["remote"],
        },
        "canada": {
            "terms": ['"Canada"', '"Toronto"', '"Vancouver"'],
            "locations": ["remote"],
        },
        "canda": {
            "terms": ['"Canada"', '"Toronto"', '"Vancouver"'],
            "locations": ["remote"],
        },
        "uk": {
            "terms": ['"UK"', '"United Kingdom"', '"London"'],
            "locations": ["remote"],
        },
        "worldwide": {
            "terms": ['"Worldwide"', '"Global"'],
            "locations": ["remote"],
        },
    }

    # Experience level signals
    EXPERIENCE_MODIFIERS = {
        "junior":  ['"junior"', '"entry level"', '"0-2 years"'],
        "mid":     ['"mid"', '"intermediate"', '"2-5 years"'],
        "senior":  ['"senior"', '"lead"', '"staff"', '"5+ years"'],
    }

    # Job type modifiers
    JOB_TYPE_MODIFIERS = {
        "full-time": ['"full-time"', '"full time"'],
        "contract":  ['"contract"', '"contractor"', '"freelance"'],
        "part-time": ['"part-time"', '"part time"'],
    }

    def build(
        self,
        keywords:   list[str],
        sites:      list[str],
        location:   Optional[str] = "remote",
        countries:  Optional[list[str]] = None,
        job_type:   Optional[str] = None,
        experience: Optional[str] = None,
        days_back:  int = 2,
    ) -> list[dict]:
        """
        Build a list of dork query dicts.
        Each dict has: { query: str, keyword: str, site: str, strategy: str }
        """
        queries = []

        # Note: DuckDuckGo / metasearch backends do not support the 'after:YYYY-MM-DD' operator
        # inside the search input box. Outbound date filtering is managed natively at the
        # search engine level using the 'timelimit' API parameter (df=d, df=w, etc.).

        # Build modifiers once
        geo_mods = self._build_geo_modifiers(location=location, countries=countries)
        type_mods = self.JOB_TYPE_MODIFIERS.get(job_type, []) if job_type else ['"full-time"', '"contract"']
        exp_mods  = self.EXPERIENCE_MODIFIERS.get(experience, []) if experience else []

        def phrase(term: str) -> str:
            term = term.strip()
            return term if term.startswith('"') and term.endswith('"') else f'"{term}"'

        for keyword in keywords:
            # Expand keyword into variants
            kw_variants = self.KEYWORD_EXPANSIONS.get(
                keyword.lower(), [f'"{keyword}"']
            )

            for site_key in sites:
                cfg = self.SITE_CONFIGS.get(site_key)
                if not cfg:
                    # Generic fallback for unknown sites
                    cfg = {"url_pattern": f"site:{site_key}", "title_signals": []}

                site_pattern = cfg["url_pattern"]

                # ── Strategy 1: intitle + site ──────────────────────────────
                # Best for platforms where job title is in the page title
                for kv in kw_variants[:1]:  # top 1 variant only to keep query counts low
                    for geo_str in geo_mods:
                        q = f'{site_pattern} intitle:{phrase(kv)} {geo_str}'.strip()
                        queries.append({
                            "query":    q,
                            "keyword":  keyword,
                            "site":     site_key,
                            "strategy": "intitle+site",
                        })

                # ── Strategy 2: inurl + keyword ──────────────────────────────
                # Hits ATS platforms (greenhouse, lever, workable) where
                # the job title appears in the URL slug
                if any(p in site_key for p in ["greenhouse", "lever", "workable", "ashby"]):
                    slug = keyword.lower().replace(" ", "-")
                    q = f'{site_pattern} inurl:{slug}'.strip()
                    queries.append({
                        "query":    q,
                        "keyword":  keyword,
                        "site":     site_key,
                        "strategy": "inurl+ats",
                    })

                # ── Strategy 3: broad keyword + type/experience ──────────────
                # Adds job_type or experience level to narrow results
                extra = (type_mods[:1] + exp_mods[:1])
                extra_str = " ".join(extra)
                for geo_str in geo_mods:
                    q = f'{site_pattern} {phrase(keyword)} {geo_str} {extra_str}'.strip()
                    queries.append({
                        "query":    q,
                        "keyword":  keyword,
                        "site":     site_key,
                        "strategy": "broad+filters",
                    })

        # ── Strategy 4: Multi-site broad queries ────────────────────────────
        # Hit multiple boards at once without site: restriction
        # Good for catching boards not in the explicit list
        for keyword in keywords[:3]:  # top 3 keywords only
            kv = f'"{keyword}"'
            for geo_str in geo_mods:
                q = f'{kv} {geo_str} job posting "apply now"'.strip()
                queries.append({
                    "query":    q,
                    "keyword":  keyword,
                    "site":     "multi-site",
                    "strategy": "broad-multi",
                })

        # Deduplicate identical query strings
        seen_q = set()
        unique = []
        for q in queries:
            if q["query"] not in seen_q:
                seen_q.add(q["query"])
                unique.append(q)
        print(f"Built {len(queries)} queries → {len(unique)} unique queries")
        for q in unique[:5]:
            print(f'  {q["strategy"]} | {q["site"]} | {q["query"][:80]}...')
        return unique

    def _build_geo_modifiers(
        self,
        location: Optional[str],
        countries: Optional[list[str]],
    ) -> list[str]:
        if not countries:
            return self.LOCATION_MODIFIERS.get(location or "remote", ['"remote"']) or [""]

        modifiers: list[str] = []

        def term_group(terms: list[str]) -> str:
            terms = terms[:4]
            if len(terms) == 1:
                return terms[0]
            return "(" + " OR ".join(terms) + ")"

        for country in countries:
            key = country.strip().lower()
            if not key:
                continue

            config = self.COUNTRY_TARGETS.get(key)
            if not config:
                config = {
                    "terms": [f'"{country.strip()}"'],
                    "locations": [location or "remote"],
                }

            country_terms = term_group(config["terms"])
            allowed_locations = config["locations"]
            if location:
                req_loc = location.strip().lower()
                if req_loc in allowed_locations:
                    allowed_locations = [req_loc]
                else:
                    allowed_locations = [req_loc]

            for mode in allowed_locations:
                mode_terms = self.LOCATION_MODIFIERS.get(mode, [])
                mode_prefixes = mode_terms[:1] if mode_terms else [""]
                for mode_prefix in mode_prefixes:
                    modifiers.append(f"{mode_prefix} {country_terms}".strip())

        seen = set()
        unique = []
        for modifier in modifiers:
            if modifier not in seen:
                seen.add(modifier)
                unique.append(modifier)
        return unique or ['"remote"']
