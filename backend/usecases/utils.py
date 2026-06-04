import os
import sys
import csv
import logging
from pathlib import Path

# Add backend root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))

from config.settings import DATABASE_URL, SITES
from scheduler.runner import run_cycle
from storage.db import init_db, recent_jobs
from config.settings import DEFAULT_INDEED_LIMIT
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("job_scraper.usecases")


def run_usecase(site_name: str, output_filename: str) -> None:
    """Run crawler for the target site and export scraped jobs to a CSV file."""
    logger.info("==================================================")
    logger.info("Executing Use Case: %s", site_name.upper())
    logger.info("==================================================")

    # 1. Setup dynamic overrides for 500-job target if indeed or linkedin
    if "indeed" in site_name:
        os.environ["INDEED_FROMAGE"] = "3"
        os.environ["INDEED_LIMIT"] = str(DEFAULT_INDEED_LIMIT)
        logger.info("Configured Indeed constraints: 3 days, 50 jobs limit")
    elif "linkedin" in site_name:
        os.environ["LINKEDIN_TPR"] = "r86400"
        logger.info("Configured LinkedIn constraints: latest 24 hours TPR")

    # Override max_pages dynamically to ensure up to 50 jobs are fetched
    for cfg in SITES:
        if cfg.name == site_name:
            if "indeed" in site_name:
                cfg.max_pages = 500
                logger.info("Overridden Indeed max_pages to 0 (unlimited)")
            elif "linkedin" in site_name:
                cfg.max_pages = 500
                logger.info("Overridden LinkedIn max_pages to 0 (unlimited)")

    logger.info("Database URL set to: %s", DATABASE_URL)

    # Initialize DB tables if they don't exist yet
    logger.info("Ensuring database tables are initialized...")
    init_db()

    # 2. Trigger Active Scraping
    logger.info("Starting crawler for %s...", site_name)
    run_cycle(site_filter=site_name)

    # 3. Retrieve jobs from the last 3 days
    logger.info("Querying PostgreSQL for jobs scraped within the last 3 days for %s...", site_name)

    try:
        rows = recent_jobs(hours=72, source=site_name)
        if not rows:
            logger.warning("No jobs found in the database for site '%s' in the last 3 days.", site_name)
            rows = []

        logger.info("Found %d jobs. Exporting to %s...", len(rows), output_filename)
        
        # Ensure output directory exists
        out_path = Path(output_filename)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "Title", "Company", "Location", "URL", "Description", 
                "Tags", "Salary", "Source", "Scraped At"
            ])
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
                
        logger.info("Usecase %s finished successfully. Exported to: %s", site_name.upper(), out_path.absolute())
        
    except Exception as e:
        logger.error("Failed to query database or write CSV file: %s", e, exc_info=True)
