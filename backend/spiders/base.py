"""
BaseJobSpider — shared spider foundation for all job-board spiders.

Every concrete spider should:
  1. Inherit from BaseJobSpider.
  2. Set `site_config` to its SiteConfig instance.
  3. Implement `extract_jobs(response)` — an async generator that yields
     raw job dicts from a single page.

The base class handles:
  - Fetcher strategy selection (http / dynamic / stealth)
  - Session configuration + proxy rotation
  - Pagination following (via next_page_selector)
  - Per-page page cap enforcement
  - Bot-block detection + tiered retry (http → stealth)
  - Deduplication via the storage layer
  - Run tracking (start_run / finish_run)
  - Structured logging
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from scrapling.spiders import Spider, SessionManager, Request, Response
from scrapling.fetchers import (
    FetcherSession,
    AsyncDynamicSession,
    AsyncStealthySession,
    ProxyRotator,
)

from config.settings import SiteConfig, CRAWL_DIR
from storage.db import save_job, start_run, finish_run


class BaseJobSpider(Spider):
    """Reusable base for all job-board spiders."""

    # Subclasses must assign this.
    site_config: SiteConfig

    # ── Spider-level defaults (overridden from SiteConfig at __init_subclass__) ──
    name: str = "base_job_spider"
    start_urls: list[str] = []
    robots_txt_obey: bool = True
    concurrent_requests: int = 4
    concurrent_requests_per_domain: int = 2
    download_delay: float = 1.5
    max_blocked_retries: int = 3

    # ── Internal state ──────────────────────────────────────────────────────
    _page_counts: dict[str, int]
    _run_id: int | None
    _items_new: int
    _items_dupe: int

    def __init_subclass__(cls, **kwargs: object) -> None:
        """
        Propagate SiteConfig values into Spider class-level attributes
        so the framework picks them up correctly.
        """
        super().__init_subclass__(**kwargs)
        cfg: SiteConfig | None = getattr(cls, "site_config", None)
        if cfg is not None:
            cls.name = cfg.name
            cls.start_urls = cfg.start_urls
            cls.robots_txt_obey = cfg.robots_txt_obey
            cls.concurrent_requests = cfg.concurrent_requests
            cls.concurrent_requests_per_domain = cfg.concurrent_requests_per_domain
            cls.download_delay = cfg.download_delay
            cls.max_blocked_retries = cfg.max_blocked_retries

    # ── Session wiring ───────────────────────────────────────────────────────

    def configure_sessions(self, manager: SessionManager) -> None:
        cfg = self.site_config
        rotator = ProxyRotator(cfg.proxies) if cfg.proxies else None

        # Always register a fast HTTP session used for retry escalation
        manager.add(
            "http",
            FetcherSession(
                impersonate=["chrome", "firefox", "safari"],
                proxy_rotator=rotator,
            ),
        )

        # Always register dynamic and stealth sessions lazily so escalation works properly
        manager.add(
            "dynamic",
            AsyncDynamicSession(
                timeout=60000,
                proxy_rotator=rotator,
            ),
            lazy=True,
        )

        manager.add(
            "stealth",
            AsyncStealthySession(
                block_webrtc=True,
                solve_cloudflare=True,
                timeout=60000,
                proxy_rotator=rotator,
            ),
            lazy=True,
        )

    def _default_sid(self) -> str:
        fetcher = self.site_config.fetcher
        return {"http": "http", "dynamic": "dynamic", "stealth": "stealth"}.get(
            fetcher, "http"
        )

    # ── Lifecycle hooks ──────────────────────────────────────────────────────

    async def on_start(self, resuming: bool = False) -> None:
        import os
        # Dynamic overrides from environment variables
        max_pages_env = os.getenv("MAX_PAGES")
        if max_pages_env is not None:
            try:
                self.site_config.max_pages = int(max_pages_env)
                self.logger.info("Dynamically overrode max_pages to %d", self.site_config.max_pages)
            except ValueError:
                pass

        self._page_counts = {}
        self._items_new = 0
        self._items_dupe = 0
        self._run_id = start_run(self.site_config.name)
        verb = "Resuming" if resuming else "Starting"
        self.logger.info(
            "%s spider [%s] | fetcher=%s | run_id=%s",
            verb,
            self.name,
            self.site_config.fetcher,
            self._run_id,
        )

    async def on_close(self) -> None:
        if self._run_id is not None:
            finish_run(
                self._run_id,
                items_new=self._items_new,
                items_dupe=self._items_dupe,
            )
        self.logger.info(
            "Spider [%s] closed | new=%d dupes=%d",
            self.name,
            self._items_new,
            self._items_dupe,
        )

    async def on_error(self, request: Request, error: Exception) -> None:
        self.logger.error("Request failed: %s — %s", request.url, error)

    async def on_scraped_item(self, item: dict) -> dict | None:
        """Persist to DB and deduplicate before adding to result list."""
        # Restrict remote job boards to jobs posted within the last 3 days
        if self.name in {"remoteok", "weworkremotely", "jobicy", "remotive", "himalayas", "trueup"}:
            date_posted = item.get("date_posted")
            from services.filters import is_within_3_days
            if not is_within_3_days(date_posted):
                self.logger.info("[%s] Dropping item older than 3 days: %s (posted: %s)", self.name, item.get("title"), date_posted)
                return None

        was_new, fp = save_job(item, source=self.site_config.name)
        if was_new:
            self._items_new += 1
            self.logger.debug("NEW job saved: %s [%s]", item.get("title"), fp[:8])
            return item
        else:
            self._items_dupe += 1
            return None  # drop dupe from in-memory results

    # ── Block detection + escalation ─────────────────────────────────────────

    async def is_blocked(self, response: Response) -> bool:
        if response.status in {401, 403, 407, 429, 444, 500, 502, 503, 504}:
            return True
        try:
            body_str = response.body.decode("utf-8", errors="ignore")
            
            # If it's a valid JSON response containing jobs or success, it's definitely NOT blocked
            if body_str.strip().startswith("{") or body_str.strip().startswith("["):
                try:
                    import json
                    data = json.loads(body_str)
                    if isinstance(data, dict) and ("jobs" in data or "success" in data or "jobCount" in data or "job-count" in data):
                        return False
                except Exception:
                    pass

            body_lower = body_str.lower()
            
            # 1. Check title for block/challenge indicators
            import re
            title_match = re.search(r"<title>(.*?)</title>", body_str, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).lower().strip()
                block_titles = {
                    "just a moment...",
                    "attention required!",
                    "access denied",
                    "security check",
                    "please verify you are not a bot",
                    "verify you are human",
                    "bot check",
                    "cloudflare",
                }
                if any(bt in title for bt in block_titles):
                    return True

            # 2. Check for precise body block/challenge indicators (avoiding generic false positives)
            precise_block_signals = [
                "access denied",
                "verify you are human",
                "bot detection",
                "403 forbidden",
                "cloudflare ray id",
                "turnstile challenge",
                "please complete the security check",
                "ddos-guard",
                "captcha-delivery",
            ]
            
            # Special case for "rate limit" to avoid matching "rate limiting" in job descriptions
            if "rate limit exceeded" in body_lower or "too many requests" in body_lower or "429 too many requests" in body_lower:
                return True
                
            if any(sig in body_lower for sig in precise_block_signals):
                return True
                
            return False
        except Exception:
            return False

    async def retry_blocked_request(
        self, request: Request, response: Response
    ) -> Request:
        """Escalate: http → dynamic → stealth."""
        current = getattr(request, "sid", "http") or "http"
        escalation = {"http": "dynamic", "dynamic": "stealth"}
        next_sid = escalation.get(current, "stealth")
        request.sid = next_sid
        self.logger.warning(
            "Blocked on %s — escalating session: %s → %s",
            request.url,
            current,
            next_sid,
        )
        
        # Adjust timeout if it exists in _session_kwargs and we are using a Playwright fetcher
        if next_sid in {"dynamic", "stealth"} and hasattr(request, "_session_kwargs") and "timeout" in request._session_kwargs:
            t = request._session_kwargs["timeout"]
            if t is not None and t < 1000:
                request._session_kwargs["timeout"] = t * 1000
                self.logger.info("Escalation: converted timeout from %d seconds to %d ms for Playwright", t, t * 1000)
                
        return request

    # ── start_requests: attach default session id ─────────────────────────────

    async def start_requests(self) -> AsyncGenerator:
        sid = self._default_sid()
        cfg = self.site_config
        kwargs = dict(cfg.extra_fetch_kwargs or {})
        
        # If starting with dynamic/stealth, and timeout is in seconds, convert to ms
        if sid in {"dynamic", "stealth"} and "timeout" in kwargs:
            t = kwargs["timeout"]
            if t is not None and t < 1000:
                kwargs["timeout"] = t * 1000
                self.logger.info("Converted start request timeout from %d seconds to %d ms for Playwright", t, t * 1000)

        for url in self.site_config.start_urls:
            yield Request(url, callback=self.parse, sid=sid, **kwargs)

    # ── Core parse: pagination loop ──────────────────────────────────────────

    async def parse(self, response: Response) -> AsyncGenerator:
        domain = response.url.split("/")[2]
        self._page_counts.setdefault(domain, 0)
        self._page_counts[domain] += 1

        self.logger.info(
            "[%s] Parsing page %d: %s",
            self.name,
            self._page_counts[domain],
            response.url,
        )

        # Yield job items from this page
        async for job in self.extract_jobs(response):
            yield job

        # Pagination — follow next page if within cap
        cfg = self.site_config
        if cfg.max_pages == 0 or self._page_counts[domain] < cfg.max_pages:
            next_href = response.css(cfg.next_page_selector).get()
            if next_href:
                kwargs = dict(cfg.extra_fetch_kwargs or {})
                next_sid = getattr(response, "meta", {}).get("sid", self._default_sid())
                if next_sid in {"dynamic", "stealth"} and "timeout" in kwargs:
                    t = kwargs["timeout"]
                    if t is not None and t < 1000:
                        kwargs["timeout"] = t * 1000
                yield response.follow(
                    next_href,
                    callback=self.parse,
                    sid=next_sid,
                    **kwargs
                )

            else:
                self.logger.debug("[%s] No next page found on %s", self.name, response.url)
        else:
            self.logger.info(
                "[%s] Page cap (%d) reached for domain %s",
                self.name,
                cfg.max_pages,
                domain,
            )

    # ── Subclass contract ────────────────────────────────────────────────────

    async def extract_jobs(self, response: Response) -> AsyncGenerator:
        """
        Override in each concrete spider.
        Should be an `async def` that yields job dicts with keys:
            title, company, location, url, description, tags, salary
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement extract_jobs()"
        )
        yield  # make it an async generator
