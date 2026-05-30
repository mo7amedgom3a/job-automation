# Job Automation Search API

This project runs a local FastAPI service that builds advanced job-search dorks, searches DuckDuckGo, parses results into normalized job objects, and feeds n8n workflows.

## Start Locally

```bash
docker compose up -d job-dork-api
```

Check that the API is healthy:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "job-dork-search",
  "time": "2026-05-26T03:28:32.643973"
}
```

## Main Search Endpoint

Endpoint:

```text
POST http://localhost:8000/search
```

Basic example:

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["devops", "terraform", "kubernetes"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "lever.co", "greenhouse.io"],
    "location": "onsite",
    "countries": ["egypt"],
    "job_type": "full-time",
    "days_back": 5,
    "recent_hours": 24,
    "posted_today": true,
    "sort_by_posted_at": true,
    "max_results": 50,
    "reset_cache": false
  }' | jq
```

Response shape:

```json
{
  "jobs": [
    {
      "id": "md5-url-hash",
      "title": "DevOps Engineer",
      "company": "Example",
      "url": "https://...",
      "description": "Short snippet...",
      "location": "Remote",
      "salary": "",
      "source": "lever",
      "dork_query": "site:jobs.lever.co ...",
      "posted_at": "2026-05-26T03:27:56.094201",
      "score": 7.5
    }
  ],
  "total_found": 22,
  "new_jobs": 50,
  "cached_skipped": 0,
  "recency_skipped": 6,
  "queries_run": 20,
  "duration_ms": 4200,
  "timestamp": "2026-05-26T03:27:56.100000"
}
```

## Use Cases

### Country and Region Targeting

Use the `countries` array to expand geographic dorks.

- `egypt`: searches remote, hybrid, and onsite jobs using Egypt/Cairo terms.
- `mena`: searches remote jobs across MENA/Middle East/Gulf terms.
- `eu` or `europe`: searches remote jobs across EU/Europe terms.
- `usa` or `us`: searches remote US jobs.
- `canada` or `canda`: searches remote Canada jobs.
- `uk`: searches remote UK jobs.
- `worldwide`: searches global remote jobs.

Unknown country names still work. For example, `"countries": ["germany"]` creates remote Germany dorks.

`days_back: 1` makes DuckDuckGo use its past-day search window and adds an `after:` dork date.

`recent_hours: 24` applies a strict API-side filter against each parsed `posted_at`. With `strict_recent: true`, jobs without a parseable timestamp are excluded instead of being treated as new.

Use `sort_by_posted_at: true` to sort newest jobs first.

### Recency Modes

Last hour only:

```json
{
  "days_back": 1,
  "recent_hours": 1,
  "strict_recent": true,
  "sort_by_posted_at": true
}
```

Today only:

```json
{
  "days_back": 1,
  "posted_today": true,
  "strict_recent": true,
  "sort_by_posted_at": true
}
```

Last 24 hours:

```json
{
  "days_back": 1,
  "recent_hours": 24,
  "strict_recent": true,
  "sort_by_posted_at": true
}
```

### 1. DevOps Remote Jobs, Latest 24 Hours

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["devops", "kubernetes", "terraform", "aws"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "weworkremotely.com", "remotive.com"],
    "location": "remote",
    "countries": ["egypt", "mena", "eu", "usa", "canada"],
    "job_type": "full-time",
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 20
  }' | jq '.jobs[] | {title, company, source, score, url}'
```

### 2. ATS-Only Search, 30+ Results

Best for direct application links from Greenhouse, Lever, Workable, and Ashby.

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["backend engineer", "platform engineer", "fastapi", "golang"],
    "job_sites": ["greenhouse.io", "lever.co", "workable.com", "jobs.ashbyhq.com"],
    "location": "remote",
    "countries": ["egypt", "mena", "eu", "usa", "canada"],
    "job_type": "full-time",
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 60
  }' | jq
```

### 3. Contract/Freelance Cloud Roles, Latest 24 Hours

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["cloud engineer", "aws", "terraform", "serverless"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "wellfound.com", "lever.co"],
    "location": "remote",
    "countries": ["mena", "eu", "usa", "canada", "uk"],
    "job_type": "contract",
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 40
  }' | jq '.jobs[] | {title, company, location, salary, score, url}'
```

### 4. Egypt Jobs: Remote, Hybrid, and Onsite

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["backend engineer", "devops", "platform engineer", "full stack engineer"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "greenhouse.io", "lever.co"],
    "location": "remote",
    "countries": ["egypt"],
    "job_type": "full-time",
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 50
  }' | jq
```

For Egypt, the generated dorks include remote, hybrid, and onsite variants automatically.

### 5. MENA/EU/USA/Canada Remote Sweep

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["terraform", "kubernetes", "python", "golang", "aws"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "remotive.com", "greenhouse.io", "lever.co"],
    "location": "remote",
    "countries": ["mena", "eu", "usa", "canada"],
    "job_type": "full-time",
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 60
  }' | jq '.jobs[] | {title, company, location, source, score, url}'
```

### 6. Fresh Scan Without API Cache

Use `reset_cache: true` when testing and you want the API to forget its in-memory URL cache.

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["python fastapi", "backend engineer"],
    "job_sites": ["lever.co", "greenhouse.io"],
    "location": "remote",
    "countries": ["egypt", "mena", "eu", "usa", "canada"],
    "days_back": 1,
    "recent_hours": 24,
    "strict_recent": true,
    "sort_by_posted_at": true,
    "max_results": 40,
    "reset_cache": true
  }' | jq
```

If a job board/search snippet does not expose a date like `2 hours ago`, `today`, `2026-05-26`, or another parseable timestamp, strict mode filters it out. Set `"strict_recent": false` if you prefer to keep unknown-date jobs and sort them after dated jobs.

## Preview Generated Dorks

Use this before a real search to inspect the generated queries.

```bash
curl "http://localhost:8000/queries/preview?keywords=devops,kubernetes&sites=linkedin.com/jobs,greenhouse.io&location=remote&countries=egypt,mena,eu,usa,canada&days_back=1" | jq
```

The builder creates four strategy types:

- `intitle+site`: best for LinkedIn, WWR, Remotive.
- `inurl+ats`: best for Greenhouse, Lever, Workable, Ashby.
- `broad+filters`: adds job type and experience filters.
- `broad-multi`: broad sweep with `job posting`, `apply now`, and `after:YYYY-MM-DD`.

## Cache Utilities

View API cache stats:

```bash
curl http://localhost:8000/cache/stats | jq
```

Clear API cache:

```bash
curl -X DELETE http://localhost:8000/cache | jq
```

Note: this API cache is separate from the n8n SQLite `seen_jobs` table. The API cache prevents duplicate URLs during local search runs, while SQLite prevents sending the same job to Telegram again.
