import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper_api.dork_builder import DorkQueryBuilder

print("Starting diagnostic scrape google search for Egypt...")
dork_builder = DorkQueryBuilder()
queries = dork_builder.build(
    keywords=["backend", "Full Stack", "engineer", "DevOps", "Cloud"],
    sites=["linkedin.com/jobs", "remotive.com"],
    location="remote",
    countries=["Egypt"]
)

for query in queries:
    print(f"Generated query: {query}")
    print("-" * 50)