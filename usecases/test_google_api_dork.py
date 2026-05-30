"""
Verification Script for standard Google Search APIs (Serper.dev / SerpApi)
with Custom Dork Templates and 24-Hour Date post-filtering.
"""

import sys
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

# Ensure the root is in sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from scraper_api.dork_builder import DorkQueryBuilder
from scraper_api.google_api_search_engine import GoogleApiSearcher
from scraper_api.parser import JobResultParser
from main import is_within_24_hours

async def main():
    print("=" * 80)
    print("  Google Search API (Serper / SerpApi) + 24-Hour Dork Search Verification")
    print("=" * 80)

    # 1. Instantiate shared components
    dork_builder = DorkQueryBuilder()
    google_searcher = GoogleApiSearcher()
    job_parser = JobResultParser()

    # 2. Build Dork template queries
    # Let's test a Remote search for linkedin, glassdoor, and remotive
    test_sites = ["linkedin.com/jobs", "remotive.com"]
    print("Building standard dork template queries for Remote...")
    queries = dork_builder.build_template_queries(
        keywords=[],  # will use the default multidisciplinary block
        sites=test_sites,
        location="remote"
    )

    print(f"\nGenerated {len(queries)} customized dork template queries:")
    for idx, q in enumerate(queries):
        print(f"  Query {idx + 1}:")
        print(f"    Site: {q['site']}")
        print(f"    Dork: {q['query']}")
    print("-" * 80)

    

    # 3. Run Google API search for the Remote queries
    print("\nExecuting Google Search via standard APIs (Serper / SerpApi)...")
    raw_results = []
    for q in queries[:2]:  # Test first 2 queries to be polite to our API quotas
        try:
            print(f"\nExecuting query for {q['site']}...")
            res = await google_searcher.search(q["query"], max_results=10)
            print(f"  Retrieved {len(res)} raw results from Google API.")
            
            # Enrich raw results with metadata needed by parser
            for r in res:
                r["_dork_query"] = q["query"]
                r["_dork_keyword"] = q["keyword"]
                r["_dork_site"] = q["site"]
                r["_dork_strategy"] = q["strategy"]
            raw_results.extend(res)
        except Exception as e:
            print(f"  Query failed: {e}")

    if not raw_results:
        print("\nNo raw results retrieved from Google API search.")
        return

    # 4. Apply strict 24-hour post-filtering
    print(f"\nApplying strict 24-hour post-filtering on {len(raw_results)} results...")
    filtered_results = []
    discarded_count = 0
    for r in raw_results:
        date_val = r.get("date", "")
        body_val = r.get("body", "")
        if is_within_24_hours(date_val, body_val):
            filtered_results.append(r)
        else:
            discarded_count += 1
            print(f"  Discarded (older than 24h): {r.get('title')} | Date: '{date_val}'")

    print(f"\nDate post-filter summary:")
    print(f"  Retained: {len(filtered_results)}")
    print(f"  Discarded: {discarded_count}")

    if not filtered_results:
        print("\nNo results remained after 24-hour post-filtering.")
        return

    # 5. Parse organic results into structured jobs
    print("\nParsing retained results...")
    parsed_jobs = job_parser.parse_many(filtered_results)
    
    print(f"\nSuccessfully parsed {len(parsed_jobs)} structured jobs:")
    for idx, job in enumerate(parsed_jobs):
        print(f"\n  Job {idx + 1}:")
        print(f"    Title:    {job.get('title')}")
        print(f"    Company:  {job.get('company')}")
        print(f"    Location: {job.get('location')}")
        print(f"    Source:   {job.get('source')}")
        print(f"    URL:      {job.get('url')}")
        print(f"    Score:    {job.get('score')}")
        print(f"    Snippet:  {job.get('description')[:120]}...")

if __name__ == "__main__":
    asyncio.run(main())
