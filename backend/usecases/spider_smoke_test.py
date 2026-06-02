"""Run one or all spiders through the scheduler for manual smoke testing.

Examples:
    python -m usecases.spider_smoke_test --site linkedin_eg
    python -m usecases.spider_smoke_test --all
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable

from config.settings import SITES
from scheduler.runner import run_spider
from storage.db import init_db, recent_jobs


def available_spiders() -> list[str]:
    return sorted(site.name for site in SITES)


def run_sites(site_names: Iterable[str], max_pages: int) -> list[dict]:
    os.environ["MAX_PAGES"] = str(max_pages)
    init_db()

    summaries = []
    for site_name in site_names:
        cfg = next((site for site in SITES if site.name == site_name), None)
        if cfg is None:
            summaries.append({"site": site_name, "status": "missing"})
            continue

        cfg.enabled = True
        cfg.max_pages = max_pages
        summary = run_spider(cfg)
        latest = recent_jobs(hours=72, source=site_name)
        summary["recent_jobs"] = len(latest)
        summaries.append(summary)
    return summaries


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test registered job spiders.")
    parser.add_argument("--site", choices=available_spiders(), help="Run one spider by name.")
    parser.add_argument("--all", action="store_true", help="Run every registered spider.")
    parser.add_argument("--max-pages", type=int, default=1, help="Page limit per spider.")
    args = parser.parse_args()

    if args.all:
        site_names = available_spiders()
    elif args.site:
        site_names = [args.site]
    else:
        parser.error("Choose --site NAME or --all.")

    for summary in run_sites(site_names, max_pages=args.max_pages):
        print(summary)


if __name__ == "__main__":
    main()
