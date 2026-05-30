"""
Verification Script for JobOrchestrator Service Layer.
"""

import sys
from pathlib import Path
import asyncio
import json

# Ensure the root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from scraper_api.orchestrator import JobOrchestrator

class MockSearchRequest:
    def __init__(self, keywords=None, job_sites=None, location="remote", countries=None, max_results=10, recent_hours=24):
        self.keywords = keywords
        self.job_sites = job_sites or ["linkedin.com/jobs", "glassdoor.com"]
        self.location = location
        self.countries = countries or ["egypt"]
        self.max_results = max_results
        self.recent_hours = recent_hours

async def main():
    print("=" * 80)
    print("  JobOrchestrator Service Layer Search Aggregator Verification")
    print("=" * 80)

    # 1. Instantiate the orchestrator
    orchestrator = JobOrchestrator()

    # 2. Build mock requests for both Remote and Cairo Onsite searches
    print("\n[TEST 1] Executing Remote Orchestrated Search...")
    remote_req = MockSearchRequest(
        keywords=["backend", "DevOps"],
        job_sites=["linkedin.com/jobs", "remotive.com"],
        location="remote",
        max_results=3,
        recent_hours=24
    )

    results = await orchestrator.orchestrate(remote_req)

    print("\n--- RESULTS SUMMARY (Remote) ---")
    for source, jobs in results.items():
        print(f"  Source: '{source}' -> Found {len(jobs)} jobs")
        for idx, job in enumerate(jobs[:2]):
            print(f"    {idx+1}. {job.get('title')} at {job.get('company')} ({job.get('location')})")
            if source == "google":
                print(f"       URL: {job.get('url')}")
                print(f"       Score: {job.get('score')}")

    print("\n" + "="*80)

    print("\n[TEST 2] Executing Cairo Onsite Orchestrated Search...")
    cairo_req = MockSearchRequest(
        keywords=["software engineer"],
        job_sites=["linkedin.com/jobs", "indeed.com"],
        location="Cairo",
        countries=["egypt"],
        max_results=3,
        recent_hours=24
    )

    cairo_results = await orchestrator.orchestrate(cairo_req)

    print("\n--- RESULTS SUMMARY (Cairo Onsite) ---")
    for source, jobs in cairo_results.items():
        print(f"  Source: '{source}' -> Found {len(jobs)} jobs")
        for idx, job in enumerate(jobs[:2]):
            print(f"    {idx+1}. {job.get('title')} at {job.get('company')} ({job.get('location')})")

if __name__ == "__main__":
    asyncio.run(main())
