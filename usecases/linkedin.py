import logging
from jobspy import scrape_jobs
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)

print("Starting diagnostic scrape for Egypt...")
job_types = ["backend", "Full Stack", "engineer", "DevOps", "Cloud"]
search_term = [f'"{job_type}"' for job_type in job_types]

linkedin_scraper = scrape_jobs(
    site_name=["linkedin"],
    search_term="'software engineer' OR backend OR 'Full Stack' OR python OR DevOps OR Cloud",
    location="Cairo, Egypt",
    is_remote=True,
    results_wanted=100,
    location_linkedin="Cairo",
    hours_old=170,
)

if linkedin_scraper is not None and not linkedin_scraper.empty:
    print(f"Scraped {len(linkedin_scraper)} jobs successfully!")
    print("\n--- JOB DETAILS ---")
    for idx, row in linkedin_scraper.iterrows():
        print(f"Title: {row.get('title')}")
        print(f"Company: {row.get('company')}")
        print(f"Location: {repr(row.get('location'))}")
        print(f"Is Remote: {repr(row.get('is_remote'))}")
        print(f"Company Addresses: {repr(row.get('company_addresses'))}")
        print("-" * 30)
else:
    print("No jobs found.")