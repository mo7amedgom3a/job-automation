"""
Hourly Scheduler
================

Runs every registered spider in sequence (or filtered by name) and
repeats on a configurable interval.  Designed to be long-lived:

    python -m scheduler.runner              # run all enabled spiders hourly
    python -m scheduler.runner --once       # single run then exit
    python -m scheduler.runner --site remoteok --once

Features
--------
- Respects `enabled` flag on each SiteConfig.
- Records each run's timing and item counts in the SQLite DB.
- Graceful Ctrl+C: waits for the active spider to finish its current page,
  then exits cleanly (Scrapling's pause/resume keeps the queue intact).
- Per-spider crawl-checkpoint directories so a crash mid-run doesn't lose
  work for subsequent spiders.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from config.settings import (
    CRAWL_DIR,
    LOG_DIR,
    SCHEDULE_INTERVAL_HOURS,
    SITES,
    SiteConfig,
)
from spiders.job_spiders import ALL_SPIDERS
from storage.db import init_db

# ─── Logging setup ───────────────────────────────────────────────────────────

def _setup_logging(log_dir: str = LOG_DIR) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "scheduler.log"

    fmt = "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        datefmt=date_fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


logger = logging.getLogger("job_scraper.scheduler")


# ─── Single-spider runner ────────────────────────────────────────────────────

def run_spider(cfg: SiteConfig) -> dict:
    """
    Instantiate and run one spider.  Returns a summary dict.
    Scrapling's Spider.start() is synchronous from the caller's perspective.
    """
    SpiderClass = ALL_SPIDERS.get(cfg.name)
    if SpiderClass is None:
        logger.warning("No spider class registered for site '%s' — skipping.", cfg.name)
        return {"site": cfg.name, "status": "skipped", "items_new": 0}

    crawl_dir = str(Path(CRAWL_DIR) / cfg.name)
    Path(crawl_dir).mkdir(parents=True, exist_ok=True)

    logger.info("▶  Starting spider: %s", cfg.name)
    t_start = time.monotonic()

    try:
        spider = SpiderClass(crawldir=crawl_dir)
        result = spider.start(use_uvloop=True)

        elapsed = time.monotonic() - t_start
        logger.info(
            "✔  Spider %s finished in %.1fs | requests=%d | items=%d | blocked=%d",
            cfg.name,
            elapsed,
            result.stats.requests_count,
            result.stats.items_scraped,
            result.stats.blocked_requests_count,
        )
        return {
            "site":       cfg.name,
            "status":     "completed" if result.completed else "paused",
            "items_new":  result.stats.items_scraped,
            "requests":   result.stats.requests_count,
            "elapsed":    round(elapsed, 2),
        }

    except KeyboardInterrupt:
        logger.info("⏸  Interrupted during %s — checkpoint saved.", cfg.name)
        raise

    except Exception as exc:
        elapsed = time.monotonic() - t_start
        logger.error("✘  Spider %s failed after %.1fs: %s", cfg.name, elapsed, exc, exc_info=True)
        return {
            "site":    cfg.name,
            "status":  "failed",
            "error":   str(exc),
            "elapsed": round(elapsed, 2),
        }


# ─── Full scrape cycle ───────────────────────────────────────────────────────

def run_cycle(site_filter: str | None = None) -> list[dict]:
    """Run all enabled spiders (optionally filtered) once."""
    targets = [
        cfg for cfg in SITES
        if cfg.enabled and (site_filter is None or cfg.name == site_filter)
    ]

    if not targets:
        logger.warning("No enabled sites to scrape%s.",
                       f" matching '{site_filter}'" if site_filter else "")
        return []

    logger.info(
        "═══ Scrape cycle started at %s | %d site(s) ═══",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        len(targets),
    )

    summaries: list[dict] = []
    for cfg in targets:
        try:
            summary = run_spider(cfg)
            summaries.append(summary)
        except KeyboardInterrupt:
            logger.info("Scheduler interrupted — exiting cycle early.")
            break

    total_new = sum(s.get("items_new", 0) for s in summaries)
    logger.info(
        "═══ Cycle complete | total new jobs: %d ═══",
        total_new,
    )
    return summaries


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Job Board Scraping Scheduler")
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single cycle then exit (instead of looping hourly).",
    )
    parser.add_argument(
        "--site", default=None, metavar="NAME",
        help="Only scrape the named site (e.g. --site remoteok).",
    )
    parser.add_argument(
        "--interval", type=int, default=SCHEDULE_INTERVAL_HOURS,
        help=f"Hours between cycles (default: {SCHEDULE_INTERVAL_HOURS}).",
    )
    args = parser.parse_args()

    _setup_logging()
    init_db()

    logger.info(
        "Job Board Scraping Engine starting | interval=%dh | once=%s | site=%s",
        args.interval,
        args.once,
        args.site or "all",
    )

    try:
        while True:
            run_cycle(site_filter=args.site)

            if args.once:
                logger.info("--once flag set. Exiting.")
                break

            sleep_secs = args.interval * 3600
            next_run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            logger.info(
                "Sleeping for %dh. Next run ~%s + %dh.",
                args.interval,
                next_run,
                args.interval,
            )
            time.sleep(sleep_secs)

    except KeyboardInterrupt:
        logger.info("Scheduler shut down by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
