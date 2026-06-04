"""Job request, response, and persistence models with OpenAPI/Swagger metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field
from config.settings import KEYWORDS, DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT, DEFAULT_SEARCH_OFFSET

class SearchRequest(BaseModel):
    keywords: list[str] = Field(
        default_factory=lambda: KEYWORDS,
        description="List of target search keywords (e.g. backend, devops, react). Used to search job descriptions and titles.",
        examples=[["backend", "python", "fastapi"]]
    )
    job_sites: list[str] = Field(
        default_factory=lambda: [
            "linkedin.com/jobs",
            "weworkremotely.com",
            "remotive.com",
            "indeed.com/jobs",
            "wellfound.com",
            "greenhouse.io",
            "lever.co",
            "workable.com",
            "jobs.ashbyhq.com",
            "jobicy.com",
        ],
        description="Target job board sites or applicant tracking system (ATS) domains to search/dork.",
        examples=[["linkedin.com/jobs", "weworkremotely.com"]]
    )
    work_type: Optional[str] = Field(
        default=None,
        description="Filter by work format: 'remote', 'onsite', or 'hybrid'. Affects Google site parsing and spider routing.",
        examples=["remote", "onsite", "hybrid"]
    )
    location: Optional[str] = Field(
        default="remote",
        description="Target city/location for onsite requests, or 'remote' for telecommuting listings.",
        examples=["remote", "Cairo", "Berlin", "San Francisco"]
    )
    countries: list[str] = Field(
        default_factory=lambda: [
            "egypt",
            "Middle East",
            "eu",
            "usa",
            "canada",
            "Germany",
            "france",
            "uk",
        ],
        description="List of country names to target. Used to select and configure country-specific spiders (e.g. linkedin_eg, indeed_sa).",
        examples=[["egypt", "Germany"]]
    )
    job_type: Optional[str] = Field(
        default=None,
        description="Specific employment type filter (e.g. fulltime, parttime, contract, internship).",
        examples=["fulltime", "contract"]
    )
    experience: Optional[str] = Field(
        default=None,
        description="Target experience level filter (e.g. junior, mid, senior, lead, architect).",
        examples=["senior", "junior"]
    )
    max_results: int = Field(
        default=DEFAULT_SEARCH_LIMIT,
        ge=1,
        le=MAX_SEARCH_LIMIT,
        description="Maximum number of unified search results to return.",
        examples=[DEFAULT_SEARCH_LIMIT]
    )
    days_back: int = Field(
        default=1,
        ge=1,
        le=60,
        description="Age of job postings in days to retrieve. Defaults to 1 day old.",
        examples=[3]
    )
    recent_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=24 * 60,
        description="Refined recency window in hours. Used for date filters.",
        examples=[24]
    )
    posted_today: bool = Field(
        default=False,
        description="Strictly limit results to jobs posted in the last 24 hours.",
        examples=[False]
    )
    strict_recent: bool = Field(
        default=True,
        description="If true, strictly ignores search items with stale timestamps or unclear date signatures.",
        examples=[True]
    )
    sort_by_posted_at: bool = Field(
        default=True,
        description="Whether to sort search results with the newest jobs first.",
        examples=[True]
    )
    reset_cache: bool = Field(
        default=False,
        description="Bypasses and clears cached query results to force a fresh orchestrator live-run.",
        examples=[False]
    )

    # Legacy/Advanced scraper configuration variables:
    easy_apply: Optional[bool] = Field(
        default=None,
        description="LinkedIn-specific filter for quick/direct application support.",
        examples=[True]
    )
    strict_country: bool = Field(
        default=False,
        description="Forces strict geo-blocking checks to filter out locations outside target countries.",
        examples=[False]
    )
    linkedin_fetch_description: bool = Field(
        default=False,
        description="LinkedIn-specific option to fetch full descriptions for parsed postings (requires more network traffic).",
        examples=[False]
    )
    linkedin_company_ids: Optional[list[int]] = Field(
        default=None,
        description="Filter listings to specific LinkedIn company IDs.",
        examples=[[12345, 67890]]
    )
    google_search_term: Optional[str] = Field(
        default=None,
        description="Overrides generated query templates with a raw Google search dork string.",
        examples=['site:greenhouse.io "backend engineer" "remote"']
    )
    distance: Optional[int] = Field(
        default=None,
        description="Radius distance in miles/kilometers for onsite job locations.",
        examples=[25]
    )
    proxies: Optional[list[str]] = Field(
        default=None,
        description="Optional lists of proxy URLs to rotate between fetcher sessions.",
        examples=[["http://user:pass@proxy.example.com:8080"]]
    )
    enforce_annual_salary: Optional[bool] = Field(
        default=None,
        description="Filter out job results that do not present a clear, verifiable yearly salary.",
        examples=[False]
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Custom user agent string to set during web crawling sessions.",
        examples=["Mozilla/5.0 ..."]
    )
    ca_cert: Optional[str] = Field(
        default=None,
        description="Custom CA Certificate for SSL/TLS verification.",
        examples=[None]
    )
    description_format: str = Field(
        default="markdown",
        description="Format of the description returned ('html', 'text', or 'markdown').",
        examples=["markdown"]
    )


class BatchSearchRequest(BaseModel):
    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of raw Google dork query strings to run in parallel.",
        examples=[['site:lever.co "python" "remote"', 'site:greenhouse.io "go" "remote"']]
    )
    max_results: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results to fetch per individual query.",
        examples=[25]
    )


class JobResult(BaseModel):
    id: str = Field(
        description="Unique MD5 hash fingerprint generated from the job URL.",
        examples=["c8a0c3e351bef018cfac52b41295b9c0"]
    )
    title: str = Field(
        description="Title of the job posting.",
        examples=["Staff Backend Engineer"]
    )
    company: str = Field(
        description="Name of the company hiring.",
        examples=["Google DeepMind"]
    )
    url: str = Field(
        description="Direct URL to the job posting.",
        examples=["https://linkedin.com/jobs/view/12345"]
    )
    description: str = Field(
        description="Brief snippet or full description of the role.",
        examples=["We are seeking a senior systems developer skilled in Python and Go..."]
    )
    location: str = Field(
        description="Physical location or remote eligibility status of the role.",
        examples=["remote", "Cairo, Egypt", "Berlin, Germany"]
    )
    salary: str = Field(
        description="Extracted salary range or pay structure, if available.",
        examples=["$120,000 - $150,000 / year", "N/A"]
    )
    source: str = Field(
        description="Original platform or job board the listing was parsed from.",
        examples=["linkedin", "indeed", "weworkremotely"]
    )
    dork_query: str = Field(
        description="The underlying Google Dork query that uncovered this job.",
        examples=['site:linkedin.com/jobs "backend" "remote"']
    )
    posted_at: str = Field(
        description="Relative or exact date when the job was posted.",
        examples=["24 hours ago", "2026-06-02"]
    )
    score: float = Field(
        description="Calculated relevance score based on keyword match density.",
        examples=[8.5]
    )


class SearchResponse(BaseModel):
    jobs: list[JobResult] = Field(
        description="List of normalized and scored job results matching the criteria."
    )
    total_found: int = Field(
        description="Total raw jobs parsed before applying deduplication and filtering.",
        examples=[120]
    )
    new_jobs: int = Field(
        description="Number of newly scraped job postings that were not present in the cache.",
        examples=[15]
    )
    cached_skipped: int = Field(
        description="Number of job postings skipped because their URLs were already marked as seen in the cache.",
        examples=[45]
    )
    recency_skipped: int = Field(
        description="Number of job postings filtered out for violating the recency threshold.",
        examples=[60]
    )
    queries_run: int = Field(
        description="Number of Google search queries executed in this run.",
        examples=[8]
    )
    duration_ms: int = Field(
        description="Total execution time in milliseconds.",
        examples=[4500]
    )
    timestamp: str = Field(
        description="ISO 8601 UTC timestamp of the search completion.",
        examples=["2026-06-02T17:59:20Z"]
    )


class JobSearchRequest(BaseModel):
    keywords: Optional[list[str]] = Field(None, description="List of keywords to match in title, description, or tags.", examples=[["python", "devops"]])
    countries: Optional[list[str]] = Field(None, description="Filter jobs by one or more country names (matched against location/tags/source).", examples=[["egypt", "germany"]])
    company: Optional[str] = Field(None, description="Filter jobs by hiring company name.", examples=["Google"])
    remote: Optional[bool] = Field(None, description="Filter remote jobs. If true, only remote jobs. If false, only non-remote.", examples=[True])
    limit: int = Field(DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="Maximum number of results to return.", examples=[DEFAULT_SEARCH_LIMIT])
    offset: int = Field(DEFAULT_SEARCH_OFFSET, ge=0, description="Offset for pagination.", examples=[DEFAULT_SEARCH_OFFSET])


class SubAggregateRequest(BaseModel):
    country: str = Field(..., description="Country name (e.g. egypt, saudi, germany).", examples=["egypt"])
    job_board: str = Field(..., description="Job board name (e.g. linkedin, indeed).", examples=["linkedin"])


class JobItem(BaseModel):
    id: str = Field(description="Unique MD5 hash fingerprint generated from the job URL.")
    title: str = Field(description="Title of the job posting.")
    company: str = Field(description="Name of the company hiring.")
    url: str = Field(description="Direct URL to the job posting.")
    description: str = Field(description="Brief snippet or full description of the role.")
    location: str = Field(description="Physical location or remote eligibility status of the role.")
    salary: str = Field(description="Extracted salary range or pay structure, if available.")
    source: str = Field(description="Original platform or job board the listing was parsed from.")
    site: str = Field(description="Alias / site domain.")
    tags: list[str] = Field(description="Associated tag list.")
    scraped_at: str = Field(description="ISO timestamp when the job was scraped.")


class JobBoardGroup(BaseModel):
    name: str = Field(description="Name of the job board (e.g. linkedin, indeed, weworkremotely).")
    jobs: list[JobItem] = Field(description="List of jobs in this board, sorted by scraped date.")


class CountryGroup(BaseModel):
    country: str = Field(description="Country name (e.g. Egypt, Saudi Arabia, Germany, Remote).")
    job_boards: list[JobBoardGroup] = Field(description="Job boards available for this country.")


class PaginatedSearchResponse(BaseModel):
    total: int = Field(description="Total number of matching job listings.")
    limit: int = Field(description="The maximum number of items requested.")
    offset: int = Field(description="The offset/starting position of the items.")
    results: list[CountryGroup] = Field(description="The paginated and grouped list of jobs.")


@dataclass(slots=True)
class JobRecord:
    title: str
    company: str
    location: str
    url: str
    description: str
    tags: list[str]
    salary: str
    source: str
    scraped_at: str
