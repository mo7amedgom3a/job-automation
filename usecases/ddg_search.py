import sys
from pathlib import Path
import asyncio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper_api.dork_builder import DorkQueryBuilder
from scraper_api.searcher import DuckDuckGoSearcher

print("Starting diagnostic scrape google search for Egypt...")
dork_builder = DorkQueryBuilder()
queries = dork_builder.build(
    keywords=["backend", "Full Stack", "engineer", "DevOps", "Cloud"],
    sites=["linkedin.com/jobs", "remotive.com"],
    location="remote",
    countries=["Egypt"]
)
searcher = DuckDuckGoSearcher(
    max_concurrent=10
)

async def main() -> None:
    responses = await searcher.search_all(queries, max_per_query=20, timelimit="d")
    if not responses:
        print("No search results found.")
        return

    # Print first raw result dict for debug verification
    print("Sample raw result dict:")
    print(responses[0])
    print("\n" + "=" * 50 + "\n")

    # Group flat results by query to print them out nicely
    from collections import defaultdict
    grouped = defaultdict(list)
    for response in responses:
        grouped[response.get("_dork_query")].append(response)

    for query, query_results in grouped.items():
        print(f"Search results for query: {query}")
        for idx, result in enumerate(query_results):
            print(f"  {idx + 1}. {result.get('title')} - {result.get('href')}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(main())
