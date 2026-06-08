"""
Central configuration for the Job Board Scraping Engine.
Adjust per-site settings here without touching spider logic.
"""

from dataclasses import dataclass, field
from typing import Literal

# ─── Fetcher Strategy ────────────────────────────────────────────────────────
# "http"     → Fetcher       (fastest, for plain HTTP job boards)
# "dynamic"  → DynamicFetcher (JS-rendered pages, moderate protection)
# "stealth"  → StealthyFetcher (Cloudflare, heavy bot detection, CAPTCHAs)

FetcherType = Literal["http", "dynamic", "stealth"]

KEYWORDS = ["software engineer", "DevOps", "backend", "AWS", "terraform", "python", "Golang", "Full Stack", "Engineer", "Devloper", ".NET", "react", "frontend", "AI", "LLM", "API"]
@dataclass
class SiteConfig:
    name: str
    start_urls: list[str]
    fetcher: FetcherType = "http"
    enabled: bool = True
    keywords: list[str] = field(default_factory=list)  # Dynamic job search keywords
    # Polite crawl settings (per-site overrides)
    concurrent_requests: int = 4
    concurrent_requests_per_domain: int = 2
    download_delay: float = 1.5        # seconds between requests
    max_blocked_retries: int = 3
    robots_txt_obey: bool = True
    # Pagination — CSS selector for "next page" link
    next_page_selector: str = "a[rel='next']::attr(href)"
    # Max pages per run (safety cap; 0 = unlimited)
    max_pages: int = 0
    # Extra kwargs forwarded to the underlying fetcher
    proxies: list[str] = field(default_factory=list)
    extra_fetch_kwargs: dict = field(default_factory=dict)
 
 
# ─── Registered Job Boards ───────────────────────────────────────────────────
# Only add sites that explicitly permit scraping in their robots.txt / ToS.
 
SITES: list[SiteConfig] = [
    SiteConfig(
        name="remoteok",
        start_urls=["https://remoteok.com/remote-dev-jobs"],
        fetcher="stealth",
        download_delay=2.0,
        next_page_selector="a.next::attr(href)",
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="weworkremotely",
        start_urls=[
            "https://weworkremotely.com/categories/remote-programming-jobs",
            "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs",
        ],
        fetcher="http",
        download_delay=2.0,
    ),
    SiteConfig(
        name="jobicy",
        start_urls=["https://jobicy.com/api/v2/remote-jobs"],
        fetcher="http",
        download_delay=1.5,
    ),
    SiteConfig(
        name="remotive",
        start_urls=["https://remotive.com/api/remote-jobs?category=software-dev"],
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="himalayas",
        start_urls=["https://himalayas.app/jobs/api"],
        fetcher="http",
        download_delay=3.0,
    ),
    SiteConfig(
        name="trueup",
        start_urls=["https://www.trueup.io/jobs"],
        fetcher="stealth",
        download_delay=3.0,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin",
        start_urls=["https://www.linkedin.com/jobs/search?location=Cairo"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="indeed",
        start_urls=["https://www.indeed.com/m/jobs"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
    # ─── LinkedIn Country-Specific Usecases ────────────────────────────────────
    SiteConfig(
        name="linkedin_sa",
        start_urls=["https://sa.linkedin.com/jobs/search?location=Saudi%20Arabia&geoId=100459316"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_eg",
        start_urls=["https://www.linkedin.com/jobs/search?location=Cairo"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_ae",
        start_urls=["https://ae.linkedin.com/jobs/search?location=United%20Arab%20Emirates&geoId=104305776"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_barcelona",
        start_urls=["https://www.linkedin.com/jobs/search?location=Barcelona&geoId=107025191"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_germany",
        start_urls=["https://de.linkedin.com/jobs/search?location=Germany&geoId=101282230"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_uk",
        start_urls=["https://uk.linkedin.com/jobs/search?location=United%20Kingdom&geoId=101165590&f_TPR=r86400&f_WT=2"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_poland",
        start_urls=["https://www.linkedin.com/jobs/search?location=Poland&geoId=105072130"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_spain",
        start_urls=["https://www.linkedin.com/jobs/search?location=Spain&geoId=105646813"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    SiteConfig(
        name="linkedin_canada",
        start_urls=["https://www.linkedin.com/jobs/search?location=Canada&geoId=101174742"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
    ),
    # ─── Indeed Country-Specific Usecases ──────────────────────────────────────
    SiteConfig(
        name="indeed_eg",
        start_urls=["https://eg.indeed.com/m/jobs"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
    SiteConfig(
        name="indeed_sa",
        start_urls=["https://sa.indeed.com/m/jobs"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
    SiteConfig(
        name="indeed_ae",
        start_urls=["https://ae.indeed.com/m/jobs"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
    SiteConfig(
        name="indeed_uk",
        start_urls=["https://uk.indeed.com/jobs?q=software+engineer&l=%22remote%22&fromage=1"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
    SiteConfig(
        name="indeed_germany",
        start_urls=["https://de.indeed.com/jobs?q=Software+Engineer&l=%22remote%22&fromage=1"],
        keywords=KEYWORDS,
        fetcher="http",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[data-dd-action-name='next-page']::attr(href), a[data-testid='pagination-page-next']::attr(href), a[aria-label='Next Page']::attr(href), a[aria-label='Next']::attr(href), a[aria-label*='Next']::attr(href)",
        extra_fetch_kwargs={
            "timeout": 30,
            "headers": {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/123.0.0.0 Mobile/15E148 Safari/604.1"
            }
        },
    ),
]

# ─── Scheduler ───────────────────────────────────────────────────────────────
SCHEDULE_INTERVAL_HOURS: int = 1      # run the full engine every hour
CRAWL_DIR: str = "crawl_checkpoints"  # pause/resume state directory
LOG_DIR: str = "logs"

# ─── Storage ─────────────────────────────────────────────────────────────────
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://job_user:job_password@postgres:5432/job_automation",
)
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", str(7 * 24 * 3600)))
DEDUP_WINDOW_HOURS: int = int(os.getenv("DEDUP_WINDOW_HOURS", "24"))

# Kept only for backwards-compatible function signatures in storage.db.
SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "jobs.db")


# ─── Central Aggregator & Limit Constants ───────────────────────────────────
DEFAULT_SEARCH_LIMIT: int = 500
MAX_SEARCH_LIMIT: int = 1000
DEFAULT_SEARCH_OFFSET: int = 0
DEFAULT_RECENT_HOURS: int = 72
DEFAULT_INDEED_LIMIT: int = 50  # 0 = no limit, fetch all available within date range
DEFAULT_MAX_PAGES: int = 0
DEFAULT_MAX_CONCURRENT_SPIDERS: int = 2
