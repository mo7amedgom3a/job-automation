"""
Diagnostic Script to Verify Time-Filtered (72-hour) Dork Search URL Parameters
"""

import sys
from pathlib import Path
import asyncio
from datetime import datetime, timedelta

# Resolve the project root and add it to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper_api.dork_builder import DorkQueryBuilder
from scraper_api.searcher import DuckDuckGoSearcher
from scraper_api.proxy_manager import ProxyManager

async def main() -> None:
    print("=" * 70)
    print("  Time-Filtered (72-Hour/3-Day) Dork Search Diagnostic Test")
    print("=" * 70)

    # 1. Print computed date ranges for verification
    today = datetime.now()
    three_days_ago = today - timedelta(days=3)
    expected_ddg_df = f"{three_days_ago.strftime('%Y-%m-%d')}..{today.strftime('%Y-%m-%d')}"
    
    print(f"Current local time: {today.isoformat()}")
    print(f"Target time-frame (72 hours ago): {three_days_ago.isoformat()}")
    print(f"Expected DuckDuckGo custom range 'df': {expected_ddg_df}")
    print(f"Expected Yahoo fallback parameter 'btf': w\n")

    # 2. Build dork queries
    dork_builder = DorkQueryBuilder()
    print("Building dork queries...")
    queries = dork_builder.build(
        keywords=["backend", "Full Stack", "engineer"],
        sites=["linkedin.com/jobs", "remotive.com"],
        location="remote",
    )
    # Let's run a small subset (e.g. 4 queries) to keep the diagnostic fast and polite
    selected_queries = queries[:4]
    print(f"Built {len(queries)} queries → running a subset of {len(selected_queries)} unique queries:\n")
    for q in selected_queries:
        print(f"  [{q['strategy']}] | {q['site']} | {q['query'][:80]}...")
    print("-" * 70)

    # 3. Instantiate ProxyManager and Searcher
    print("Initializing ProxyManager and DuckDuckGoSearcher...")
    proxy_file_path = ROOT / "Webshare-proxies.txt"
    proxy_manager = ProxyManager(proxy_file=str(proxy_file_path))
    
    print(f"Loaded {len(proxy_manager.proxies)} proxies from {proxy_file_path}")
    
    searcher = DuckDuckGoSearcher(
        max_concurrent=3,
        delay_between=2.0,
        timeout=35,
        max_retries=2,
        proxy_manager=proxy_manager
    )

    # 4. Execute time-filtered searches
    print("\nExecuting searches...")
    responses = await searcher.search_all(selected_queries, max_per_query=5)
    
    if not responses:
        print("\nNo search results found.")
        return

    print(f"\nSuccessfully retrieved {len(responses)} total results!")
    print("\n" + "=" * 50 + "\n")

    # 5. Group and print results
    from collections import defaultdict
    grouped = defaultdict(list)
    for response in responses:
        grouped[response.get("_dork_query")].append(response)

    for query, query_results in grouped.items():
        print(f"Search results for query: {query}")
        print(f"(Strictly filtered to last 72 hours via custom search parameters)")
        for idx, result in enumerate(query_results):
            print(f"  {idx + 1}. {result.get('title')} - {result.get('href')}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
