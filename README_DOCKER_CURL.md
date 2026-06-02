# Docker & API Query Guide

This guide explains how to build, run, and query the unified FastAPI Job Aggregator application within a Docker environment.

---
## 0. Running Application in local with fastapi 
source .venv/bin/activate
pip3 install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
## 1. Running the Application via Docker

### A. Using Docker Compose (Recommended)

To rebuild the container with the updated base image and install the required scraping browsers:

```bash
docker compose build job-dork-api
```

To run the container in the background (detached mode):

```bash
docker compose up -d job-dork-api
```

To inspect runtime execution logs:

```bash
docker compose logs -f job-dork-api
```

### B. Using Standalone Docker CLI

If you prefer building and running the container manually without docker-compose:

```bash
# Build the image from the scraper_api context
docker build -t job-aggregator ./scraper_api

# Run the container mapping port 8000
docker run -d -p 8000:8000 --name job-aggregator job-aggregator
```

---

## 2. Verifying Service Health

Once the container is running, verify that it is healthy and the API is reachable:

```bash
curl http://localhost:8000/health
```

### Expected Response

```json
{
  "status": "ok",
  "service": "job-aggregator-service",
  "time": "2026-06-02T03:55:00.123456"
}
```

---

## 3. Querying the Aggregated Endpoints via `curl`

The API accepts JSON request bodies specifying search terms, locations, and time recency constraints.

### A. Unified Aggregated Search (`POST /search/aggregate`)

This endpoint crawls all spiders in parallel and aggregates the results into a single **flat list of jobs** filtered according to your parameters.

```bash
curl -X POST http://localhost:8000/search/aggregate \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["backend", "DevOps"],
    "location": "remote",
    "countries": ["egypt", "saudi arabia"],
    "max_results": 10,
    "recent_hours": 24,
    "reset_cache": false
  }' | jq
```

### B. Grouped Orchestration Search (`POST /search/orchestrate`)

This endpoint runs target spiders in parallel and returns results **grouped by source** (`"linkedin"`, `"indeed"`, `"google"`).

```bash
curl -X POST http://localhost:8000/search/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["software engineer"],
    "location": "remote",
    "countries": ["egypt"],
    "max_results": 5,
    "recent_hours": 72
  }' | jq
```

### C. Onsite Search Example

To fetch Cairo-based **onsite** roles (which runs the Egypt-specific spiders `linkedin_eg` and `indeed_eg` in parallel):

```bash
curl -X POST http://localhost:8000/search/aggregate \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["software engineer"],
    "work_type": "onsite",
    "location": "Cairo",
    "countries": ["egypt"],
    "max_results": 5,
    "recent_hours": 24
  }' | jq
```

### D. Clear Cache Endpoint (`DELETE /cache`)

To flush the deduplication database cache and scrape duplicate URLs:

```bash
curl -X DELETE http://localhost:8000/cache
```

---

## 4. Summary of API Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `keywords` | Array of strings | `["devops", ...]` | Search terms to query. |
| `location` | String | `"remote"` | `"remote"` or a specific city like `"Cairo"`. |
| `countries` | Array of strings | `["egypt", ...]` | Target countries to determine country-specific spiders. |
| `work_type` | String | `null` | Set to `"remote"` or `"onsite"`. |
| `max_results` | Integer | `50` | Maximum number of records to return. |
| `recent_hours` | Integer | `24` | Cutoff hours old to filter jobs (`24` or `72`). |
| `reset_cache` | Boolean | `false` | If `true`, resets the duplicate URL cache. |
