import time
from duckduckgo_search import DDGS

queries = [
    'site:linkedin.com/jobs/view intitle:"backend" "remote"',
    'site:linkedin.com/jobs/view intitle:"python" "remote"',
    'site:linkedin.com/jobs/view intitle:"data engineer" "remote"'
]
MY_PROXY = "socks5h://127.0.0.1:9150"
def search_job_queries(query_list):
    all_jobs = []
    
    for q in query_list:
        print(f"Searching for: {q}")
        
        try:
            # Move the context manager INSIDE the loop. 
            # This prevents a timeout on Query 1 from crashing Queries 2 & 3.
            # We also add an explicit timeout parameter (if supported by your version).
            with DDGS(timeout=20, proxy=MY_PROXY) as ddgs:
                results = ddgs.text(
                    keywords=q,
                    timelimit="w", 
                    max_results=10
                )
                
                # Some versions of the library return None if no results are found
                if results:
                    for result in results:
                        all_jobs.append({
                            "query": q,
                            "title": result.get("title"),
                            "url": result.get("href")
                        })
                        
        except Exception as e:
            print(f"  -> An error occurred: {e}")
            
        print("  -> Pausing for 5 seconds to prevent rate limiting...\n")
        time.sleep(5) 
            
    return all_jobs

# Run the scraper
found_jobs = search_job_queries(queries)

# Print the results
print("--- Found Jobs ---")
if not found_jobs:
    print("No jobs found or all queries timed out.")
else:
    for job in found_jobs:
        print(f"Title: {job['title']}")
        print(f"Link: {job['url']}\n")