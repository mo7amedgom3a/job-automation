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


@dataclass
class SiteConfig:
    name: str
    start_urls: list[str]
    fetcher: FetcherType = "http"
    enabled: bool = True
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
        start_urls=["https://www.linkedin.com/jobs/search?keywords=Software%20Engineer&location=Cairo&geoId=101131993&distance=25&f_TPR=r86400"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="indeed",
        start_urls=["https://www.indeed.com/jobs?q=%22software+engineer%22+OR+DevOps+OR+backend+OR+AWS+OR+terraform+OR+python+OR+Golang&l=&fromage=3&sc=0kf%3Aattr%28DSQF7%29%3B&from=searchOnDesktopSerp"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[aria-label='Next Page']::attr(href)",
        extra_fetch_kwargs={"network_idle": True},
    ),
    # ─── LinkedIn Country-Specific Usecases ────────────────────────────────────
    SiteConfig(
        name="linkedin_sa",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%2BEngineer%22%2BOR%2BBackend%2BOR%2BDecOps%2BOr%2BPython%2BOR%2BGolang&location=Saudi%2BArabia&geoId=100459316&f_TPR=r86400&currentJobId=4421688413&position=4&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_eg",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DevOps%20OR%20AWS%20OR%20Cloud%20OR%20Python%20OR%20%22FUll%20AI%20Stack%22&location=Cairo&geoId=101131993&distance=25"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_ae",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=United%20Arab%20Emirates&geoId=104305776&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_barcelona",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=Barcelona&geoId=107025191&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_germany",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=Germany&geoId=101282230&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_poland",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=Poland&geoId=105072130&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_spain",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=Spain&geoId=105646813&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="linkedin_canada",
        start_urls=["https://www.linkedin.com/jobs/search?keywords=%22Software%20Engineer%22%20OR%20Backend%20OR%20DecOps%20Or%20Python%20OR%20Golang&location=Canada&geoId=101174742&f_TPR=r86400&f_WT=2&position=1&pageNum=0"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        extra_fetch_kwargs={"network_idle": True},
    ),
    # ─── Indeed Country-Specific Usecases ──────────────────────────────────────
    SiteConfig(
        name="indeed_eg",
        start_urls=["https://eg.indeed.com/jobs?q=%22software+engineer%22+OR+backend+OR+DevOps+OR+AWS+OR+Cloud+OR+python+OR+Golang&l=Cairo"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[aria-label='Next Page']::attr(href)",
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="indeed_sa",
        start_urls=["https://sa.indeed.com/jobs?q=%22software+engineer%22+OR+backend+OR+DevOps+OR+AWS+OR+Cloud+OR+python+OR+Golang&l=%22remote%22"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[aria-label='Next Page']::attr(href)",
        extra_fetch_kwargs={"network_idle": True},
    ),
    SiteConfig(
        name="indeed_ae",
        start_urls=["https://ae.indeed.com/jobs?q=%22Software+Engineer%22+OR+backend+OR+DevOps+OR+AWS+OR+cloud+OR+Python+OR+%22FUll+Stack%22"],
        fetcher="stealth",
        download_delay=3.0,
        robots_txt_obey=False,
        next_page_selector="a[aria-label='Next Page']::attr(href)",
        extra_fetch_kwargs={"network_idle": True},
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
