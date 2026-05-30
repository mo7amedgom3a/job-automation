import logging
from jobspy import scrape_jobs

logging.basicConfig(level=logging.INFO)

print("Starting diagnostic scrape for Egypt...")
job_types = ["backend", "Full Stack", "engineer", "DevOps", "Cloud"]
search_term = [f'"{job_type}"' for job_type in job_types]
indeed_scraper = scrape_jobs(
    site_name=["indeed"],
    search_term=" OR ".join(search_term),
    location="Cairo",
    country_indeed="Egypt",
    results_wanted=50,
    hours_old=72
)

if indeed_scraper is not None and not indeed_scraper.empty:
    print(f"Scraped {len(indeed_scraper)} jobs successfully!")
    print("\n--- JOB DETAILS ---")
    for idx, row in indeed_scraper.iterrows():
        print(f"Title: {row.get('title')}")
        print(f"Company: {row.get('company')}")
        print(f"Location: {repr(row.get('location'))}")
        print(f"Company Addresses: {repr(row.get('company_addresses'))}")
        print("-" * 30)
else:
    print("No jobs found.")
