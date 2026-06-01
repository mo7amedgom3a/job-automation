import os
import sys
import csv
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root and package to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
sys.path.insert(0, str(Path(__file__).parent.parent.absolute() / "job_scraper_engine"))

# Resolve absolute database path before any other imports so they pick it up from env
root_path = Path(__file__).parent.parent.absolute()
db_path = root_path / "job_scraper_engine" / "jobs.db"
if not db_path.exists() and (root_path / "jobs.db").exists():
    db_path = root_path / "jobs.db"

os.environ["SQLITE_DB_PATH"] = str(db_path)

from config.settings import SITES, SQLITE_DB_PATH
from scheduler.runner import run_cycle
from storage.db import init_db, _conn

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

    # 1. Setup dynamic overrides for 50-job target if indeed or linkedin
    if "indeed" in site_name:
        os.environ["INDEED_FROMAGE"] = "3"
        os.environ["INDEED_LIMIT"] = "50"
        logger.info("Configured Indeed constraints: 3 days, 50 jobs limit")
    elif "linkedin" in site_name:
        os.environ["LINKEDIN_TPR"] = "r86400"
        logger.info("Configured LinkedIn constraints: latest 24 hours TPR")

    # Override max_pages dynamically to ensure up to 50 jobs are fetched
    for cfg in SITES:
        if cfg.name == site_name:
            if "indeed" in site_name:
                cfg.max_pages = 5
                logger.info("Overridden Indeed max_pages to 5")
            elif "linkedin" in site_name:
                cfg.max_pages = 5
                logger.info("Overridden LinkedIn max_pages to 5")

    logger.info("Database path set to: %s", SQLITE_DB_PATH)

    # Initialize DB tables if they don't exist yet
    logger.info("Ensuring database tables are initialized...")
    init_db(SQLITE_DB_PATH)

    # 2. Trigger Active Scraping
    logger.info("Starting crawler for %s...", site_name)
    run_cycle(site_filter=site_name)

    # 3. Retrieve Jobs from the last 3 days
    logger.info("Querying SQLite DB for jobs scraped within the last 3 days for %s...", site_name)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    
    query = """
        SELECT title, company, location, url, description, tags, salary, source, scraped_at 
          FROM jobs 
         WHERE source = ? AND scraped_at >= ?
      ORDER BY scraped_at DESC
    """
    
    try:
        with _conn(str(db_path)) as conn:
            rows = conn.execute(query, [site_name, cutoff]).fetchall()
            
        if not rows:
            logger.warning("No jobs found in the database for site '%s' in the last 3 days.", site_name)
            # Write an empty CSV with headers to be consistent
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
