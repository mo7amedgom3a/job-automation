# Job Dork Search Service API Usage

This document describes how to interact with the FastAPI service exposed by `scraper_api/app.py`.

## Base URL

When running locally, the service is typically available at:

`http://127.0.0.1:8000`

If you run it behind Docker or a reverse proxy, replace the host and port accordingly.

---

## Endpoints

### 1. Health Check

`GET /health`

Response:

```json
{
  "status": "ok",
  "service": "job-dork-search",
  "time": "2026-05-27T00:00:00.000000"
}
```

---

### 2. Search Jobs

`POST /search`

Request body type: `SearchRequest`

Default body values:

```json
{
  "keywords": [
    "devops",
    "kubernetes",
    "terraform",
    "aws",
    "python",
    "golang",
    "fastapi"
  ],
  "job_sites": [
    "linkedin.com/jobs",
    "weworkremotely.com",
    "remotive.com",
    "indeed.com/jobs",
    "wellfound.com",
    "greenhouse.io",
    "lever.co",
    "workable.com",
    "jobs.ashbyhq.com",
    "jobicy.com"
  ],
  "location": "remote",
  "countries": [
    "egypt",
    "Middle East",
    "eu",
    "usa",
    "canada",
    "Germany",
    "france",
    "uk"
  ],
  "job_type": null,
  "experience": null,
  "max_results": 50,
  "days_back": 1,
  "recent_hours": 24,
  "posted_today": false,
  "strict_recent": true,
  "sort_by_posted_at": true,
  "reset_cache": false
}
```

Notes:
- `days_back` is limited to `1..3`.
- `recent_hours` is limited to `1..1440`.
- `max_results` is limited to `1..200`.

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["python", "fastapi"],
    "job_sites": ["linkedin.com/jobs"],
    "location": "remote",
    "countries": ["usa"],
    "max_results": 10,
    "days_back": 1,
    "recent_hours": 24
  }'
```

Response model: `SearchResponse`

Example response:

```json
{
  "jobs": [
    {
      "id": "abc123",
      "title": "Senior Python Developer",
      "company": "Example Co",
      "url": "https://example.com/job/abc123",
      "description": "Remote Python developer role...",
      "location": "Remote",
      "salary": "",
      "source": "linkedin.com/jobs",
      "dork_query": "site:linkedin.com/jobs ...",
      "posted_at": "2026-05-27T12:00:00Z",
      "score": 0.92
    }
  ],
  "total_found": 120,
  "new_jobs": 10,
  "cached_skipped": 5,
  "recency_skipped": 3,
  "queries_run": 20,
  "duration_ms": 450,
  "timestamp": "2026-05-27T12:00:00.000000"
}
```

Meaning of fields:
- `jobs`: normalized job records returned after deduplication and recency filtering.
- `total_found`: raw total count of parsed job results before filtering.
- `new_jobs`: number of jobs returned in this request.
- `cached_skipped`: results skipped because the URL was already seen in the cache.
- `recency_skipped`: results skipped for being older than the requested recency criteria.
- `queries_run`: number of dork queries executed.
- `duration_ms`: elapsed processing time in milliseconds.
- `timestamp`: response generation time.

---

### 3. Preview Dork Queries

`GET /queries/preview`

Query parameters:
- `keywords` - comma-separated keywords list
- `sites` - comma-separated job site domains
- `location` - location text
- `countries` - comma-separated country/location segments
- `job_type` - optional job type string
- `experience` - optional experience level string
- `days_back` - integer range `1..60`

Default preview URL:

`/queries/preview?keywords=devops,kubernetes,terraform&sites=linkedin.com/jobs,weworkremotely.com,greenhouse.io,lever.co&location=remote&countries=egypt,mena,eu,usa,canada`

Example request:

```bash
curl "http://127.0.0.1:8000/queries/preview?keywords=devops,kubernetes&sites=linkedin.com/jobs,greenhouse.io&location=remote&countries=egypt,mena,eu,usa,canada&days_back=1"
Example response:

```json
{
  "queries": [
    "site:linkedin.com/jobs ...",
    "site:weworkremotely.com ..."
  ],
  "count": 10
}
```

This endpoint is useful to verify how the service builds search dork queries.

---

### 4. Batch Search

`POST /batch-search`

Request body type: `BatchSearchRequest`

Default body shape:

```json
{
  "queries": [
    "site:example.com jobs python remote",
    "site:another.com jobs devops"
  ],
  "max_results": 25
}
```

Constraints:
- `queries` must contain at least 1 and at most 100 entries.
- `max_results` is limited to `1..100`.

Example request:

```bash
curl -X POST "http://127.0.0.1:8000/batch-search" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["site:linkedin.com/jobs python remote"],
    "max_results": 10
  }'
```

Example response:

```json
{
  "jobs": [
    {
      "id": "abc123",
      "title": "Python Engineer",
      "company": "Example Co",
      "url": "https://example.com/job/abc123",
      "description": "...",
      "location": "Remote",
      "salary": "",
      "source": "linkedin.com/jobs",
      "dork_query": "site:linkedin.com/jobs python remote",
      "posted_at": "2026-05-27T12:00:00Z",
      "score": 0.91
    }
  ],
  "results": [
    {
      "query": "site:linkedin.com/jobs python remote",
      "keyword": "",
      "site": "custom",
      "strategy": "custom",
      "results": []
    }
  ],
  "organic": [
    {
      "query": "site:linkedin.com/jobs python remote",
      "keyword": "",
      "site": "custom",
      "strategy": "custom",
      "results": []
    }
  ],
  "count": 1,
  "queries_run": 1
}
```

Notes:
- `jobs` contains parsed job records.
- `results` and `organic` contain raw search responses returned by the searcher.

---

### 5. Clear Cache

`DELETE /cache`

Response example:

```json
{
  "cleared": 42,
  "message": "Removed 42 seen URLs"
}
```

This removes all cached seen URLs so future `/search` requests can return previously seen jobs again.

---

### 6. Cache Statistics

`GET /cache/stats`

Example response:

```json
{
  "seen_urls": 42,
  "oldest_entry": "2026-05-26T11:00:00.000000"
}
```

This endpoint returns current cache size and the oldest cache timestamp.

---

## Notes

- `reset_cache` in `/search` clears the cache before processing the request.
- `sort_by_posted_at` controls whether returned jobs are sorted by posted date first.
- `strict_recent` drops jobs with unknown `posted_at` values when enabled.
- `posted_today` requires jobs to have a posted date matching the request day.

## OpenAPI / Swagger

FastAPI exposes interactive docs at:

- `GET /docs`
- `GET /redoc`

These are available when the service is running.
