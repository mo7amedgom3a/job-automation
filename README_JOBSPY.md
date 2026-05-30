# JobSpy Scraper Service Integration Guide

This guide explains how to leverage the newly integrated `python-jobspy` secondary search engine in your FastAPI service.

`python-jobspy` is a robust, free, and open-source python scraping library that queries **LinkedIn**, **Indeed**, **Glassdoor**, **Google Jobs**, and **ZipRecruiter** concurrently in a single function call, returning raw structured job posts.

---

## Endpoint Specification

*   **URL**: `http://localhost:8000/search/jobspy`
*   **Method**: `POST`
*   **Content-Type**: `application/json`

### Supported Payload Fields (Mapped dynamically from `SearchRequest`)

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`keywords`** | `list[str]` | *Required* | List of keywords to search. Joined with `OR` under the hood. |
| **`job_sites`** | `list[str]` | *All* | Target sites to query. Translates domains (e.g., `linkedin.com/jobs` -> `linkedin`, `indeed.com/jobs` -> `indeed`, `glassdoor.com` -> `glassdoor`). |
| **`location`** | `str` | `"remote"` | Scrapes specific locations. If `"remote"`, filters remote-only jobs. |
| **`countries`** | `list[str]` | `["usa"]` | Country target filter for indeed/google searches. Automatically normalized to library cased versions. |
| **`job_type`** | `str` | `null` | Filters by `fulltime`, `parttime`, `internship`, or `contract`. Synonyms (e.g. `full-time`) are auto-mapped. |
| **`max_results`** | `int` | `50` | Maximum number of results wanted across all boards. |
| **`days_back`** / **`recent_hours`** | `int` | `72` | Filter jobs posted within this time window (in hours). |
| **`easy_apply`** | `bool` | `null` | Filters for quick apply postings (Indeed/LinkedIn only). |
| **`linkedin_fetch_description`**| `bool` | `false` | Scrapes complete job bodies and direct URLs on LinkedIn (adds `O(n)` requests). |
| **`linkedin_company_ids`** | `list[int]`| `null` | Restricts LinkedIn search to specific company IDs. |
| **`google_search_term`** | `str` | `null` | Explicit search override for Google Jobs. If omitted, a dynamic fallback term is auto-constructed. |
| **`distance`** | `int` | `50` | Radius distance filter in miles. |
| **`proxies`** | `list[str]`| `null` | Proxies list in `user:pass@host:port` format for round-robin rotation. |
| **`user_agent`** | `str` | `null` | Override default user agent. |

---

## 1. Platform-Specific Safeguards & Priority Resolvers

Job boards are aggressive and enforce strict parameter constraints. The backend handles these constraints **fully transparently**:

*   **Indeed & Glassdoor**: `hours_old`, `job_type & is_remote`, and `easy_apply` are mutually exclusive. We apply an automatic priority resolver:
    1.  `easy_apply` (if explicitly requested, drops others)
    2.  `job_type` / `is_remote` (if provided, drops `hours_old`)
    3.  `hours_old` (fallback default)
*   **LinkedIn**: `hours_old` and `easy_apply` are mutually exclusive. Enforces `easy_apply` if requested, otherwise falls back to `hours_old`. Still respects `job_type`, `is_remote`, and description scraping simultaneously.
*   **Google Jobs**: Strictly uses `google_search_term`. If you do not specify one, the engine dynamically builds a highly optimized term (e.g. `"software engineer jobs near San Francisco, CA since yesterday"`).
*   **ZipRecruiter & Bayt**: Only forwards their respective supported filters (`location` and `search_term`) to ensure maximum stability.

---

## 2. Quick Verification via Curl

Run the following command in your terminal to fetch jobs concurrently using `python-jobspy`:

```bash
curl -X POST "http://localhost:8000/search/jobspy" \
  -H "Content-Type: application/json" \
  -d '{    
    "keywords": ["python", "fastapi", "backend"],
    "job_sites": ["linkedin.com/jobs", "indeed.com/jobs"],
    "location": "remote",
    "countries": ["usa"],
    "max_results": 10,
    "days_back": 3
  }' | jq
```

### Exemplary JSON Response

```json
[
  {
    "id": "li-4417836167",
    "site": "linkedin",
    "job_url": "https://www.linkedin.com/jobs/view/4417836167",
    "job_url_direct": "",
    "title": "Web Developer (HTML,CSS) | Remote",
    "company": "Crossing Hurdles",
    "location": "Remote",
    "date_posted": "2026-05-24",
    "job_type": "fulltime",
    "salary_source": "",
    "interval": "",
    "min_amount": "",
    "max_amount": "",
    "currency": "",
    "is_remote": true,
    "job_level": "entry",
    "job_function": "Engineering",
    "listing_type": "",
    "emails": "",
    "description": "Crossing Hurdles is hiring a remote HTML/CSS Web Developer...",
    "company_industry": "Information Technology",
    "company_url": "https://www.linkedin.com/company/crossinghurdles",
    "company_logo": "",
    "company_url_direct": "",
    "company_addresses": "",
    "company_num_employees": "",
    "company_revenue": "",
    "company_description": "",
    "skills": "HTML, CSS",
    "experience_range": "0-2 years",
    "company_rating": "",
    "company_reviews_count": "",
    "vacancy_count": "",
    "work_from_home_type": ""
  }
]
```

> [!TIP]
> - All `NaN` float values and `NaT` Pandas timestamps are automatically sanitized by our backend and returned as clean, empty strings (`""`) to ensure standard JSON compliance and prevent parsing errors.

---

## 3. Integrating with n8n

To wire this up in your existing **n8n workflow**:

1.  **Add an HTTP Request Node** in your workflow.
2.  Set the **Method** to `POST`.
3.  Set the **URL** to `{{$env.SEARCH_API_URL}}/search/jobspy` or `http://job-dork-api:8000/search/jobspy`.
4.  Set the **Authentication** to `None`.
5.  Under **Body Parameters**, choose **JSON** and paste a dynamic body:
    ```json
    {
      "keywords": ["devops", "terraform", "kubernetes"],
      "job_sites": ["linkedin.com/jobs", "indeed.com/jobs"],
      "location": "remote",
      "countries": ["egypt"],
      "max_results": 50,
      "days_back": 7
    }
    ```
6.  Click **Execute Node** to scrape live results. You can now pass the returned array directly to your Slack/Telegram notification and filters node!
