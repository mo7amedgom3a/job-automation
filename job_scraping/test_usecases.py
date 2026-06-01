#!/usr/bin/env python3
"""
Test Usecases Script
====================

This script automates testing the job boards scrapers with specific constraints:
  1. Set Indeed to retrieve jobs from the last 3 days and fetch up to 50 jobs.
  2. Set LinkedIn to retrieve jobs from the last 3 days and fetch up to 50 jobs.
  3. Save all newly scraped and recent jobs (within the last 3 days) into a CSV file.

Usage:
  python3 test_usecases.py --site indeed --output indeed_jobs.csv
  python3 test_usecases.py --site linkedin --output linkedin_jobs.csv
  python3 test_usecases.py --site all --output all_jobs.csv
"""

from __future__ import annotations

import os
import sys
import csv
import argparse
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the current directory and job_scraper_engine to python path
sys.path.insert(0, str(Path(__file__).parent.absolute()))
sys.path.insert(0, str(Path(__file__).parent.absolute() / "job_scraper_engine"))

from config.settings import SITES
from spiders.job_spiders import ALL_SPIDERS
from scheduler.runner import run_cycle
from storage.db import SQLITE_DB_PATH, _conn

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("job_scraper.usecases")


def setup_test_configs(site_filter: str | None = None) -> None:
    """Configure environment variables and dynamically adjust site configurations."""
    logger.info("Setting up dynamic scraping environments...")

    # 1. Setup Indeed dynamic search variables
    os.environ["INDEED_FROMAGE"] = "3"
    os.environ["INDEED_LIMIT"] = "50"
    logger.info("Indeed configured: INDEED_FROMAGE=3, INDEED_LIMIT=50")

    # 2. Setup LinkedIn dynamic search variables (3 days = 259200 seconds)
    os.environ["LINKEDIN_TPR"] = "r259200"
    logger.info("LinkedIn configured: LINKEDIN_TPR=r259200 (3 days)")

    # 3. Dynamic config adjustments in memory
    for cfg in SITES:
        if site_filter is not None and cfg.name != site_filter:
            continue

        if cfg.name == "indeed":
            # Indeed returns 15 jobs per page. To fetch 50 jobs, we need at least 4 pages.
            cfg.max_pages = 5
            logger.info("Indeed SiteConfig overridden: max_pages set to %d", cfg.max_pages)
        elif cfg.name == "linkedin":
            # LinkedIn returns 25 jobs per page. To fetch 50 jobs, we need at least 2 pages.
            cfg.max_pages = 3
            logger.info("LinkedIn SiteConfig overridden: max_pages set to %d", cfg.max_pages)


def export_jobs_to_csv(days: int, output_file: str, site_filter: str | None = None) -> None:
    """Query the SQLite database for jobs within the target window and save them to CSV."""
    logger.info("Retrieving jobs from the last %d days...", days)
    
    # 3 days ago timestamp
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    query = "SELECT title, company, location, url, description, tags, salary, source, scraped_at FROM jobs WHERE scraped_at >= ?"
    params = [cutoff]
    
    if site_filter and site_filter != "all":
        query += " AND source = ?"
        params.append(site_filter)
        
    query += " ORDER BY scraped_at DESC"
    
    db_path = os.environ.get("SQLITE_DB_PATH", SQLITE_DB_PATH)
    logger.info("Querying database: %s", db_path)
    
    try:
        with _conn(db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            
        if not rows:
            logger.warning("No jobs found in the database within the last %d days matching filter '%s'.", days, site_filter or "all")
            return
            
        logger.info("Found %d jobs. Exporting to %s...", len(rows), output_file)
        
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # Write header
            writer.writerow([
                "Title", "Company", "Location", "URL", "Description", 
                "Tags", "Salary", "Source", "Scraped At"
            ])
            
            # Write rows
            for row in rows:
                writer.writerow([
                    row["title"],
                    row["company"],
                    row["location"],
                    row["url"],
                    row["description"],
                    row["tags"],
                    row["salary"],
                    row["source"],
                    row["scraped_at"],
                ])
                
        logger.info("Successfully exported %d jobs to %s", len(rows), output_file)
        
    except Exception as e:
        logger.error("Failed to query database or write CSV file: %s", e, exc_info=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Job Boards and Export to CSV")
    parser.add_argument(
        "--site", "-s", default="all", choices=["all"] + list(ALL_SPIDERS.keys()),
        help="Site to scrape and test (default: all)"
    )
    parser.add_argument(
        "--days", "-d", type=int, default=3,
        help="Fetch jobs scraped within the last N days (default: 3)"
    )
    parser.add_argument(
        "--output", "-o", default="scraped_jobs.csv",
        help="CSV output file name (default: scraped_jobs.csv)"
    )
    parser.add_argument(
        "--no-scrape", action="store_true",
        help="Skip the active scraping step and just export existing db records"
    )
    args = parser.parse_args()

    # Define the absolute db path if we are running in package or root
    if Path("job_scraper_engine/jobs.db").exists():
        os.environ["SQLITE_DB_PATH"] = "job_scraper_engine/jobs.db"
    elif Path("jobs.db").exists():
        os.environ["SQLITE_DB_PATH"] = "jobs.db"
    else:
        # Fallback to default
        os.environ["SQLITE_DB_PATH"] = "job_scraper_engine/jobs.db"

    # Step 1: Configure site overrides & environment variables
    site_filter = None if args.site == "all" else args.site
    setup_test_configs(site_filter=site_filter)

    # Step 2: Run active crawl unless bypassed
    if not args.no_scrape:
        logger.info("Initiating active scrape cycle for site: %s", args.site)
        run_cycle(site_filter=site_filter)
    else:
        logger.info("Scrape cycle bypassed via --no-scrape.")

    # Step 3: Query DB and export to CSV
    export_jobs_to_csv(days=args.days, output_file=args.output, site_filter=site_filter)


if __name__ == "__main__":
    main()
