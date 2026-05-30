# Frontend Integration & Use-Case Specification

This document provides a comprehensive specification for the frontend development team to build user interface filters, sorting components, search payloads, and results mapping for the concurrent job search API.

---

## 1. Request Body Parameters (Payload Schema)

The POST endpoint `http://localhost:8000/search/jobspy` accepts the following parameters. Use this table to design your frontend form controls, filters, and validation rules:

### Core Search Fields
| Parameter | UI Control | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`keywords`** | Tag Input / Text List | `list[str]` | *Required* | List of job titles or skills (e.g. `["FastAPI", "Go"]`). Will be joined with `OR` under the hood. |
| **`job_sites`** | Multi-Select Checkboxes | `list[str]` | `["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"]` | Target platforms. Allowed domains: `linkedin.com/jobs`, `indeed.com/jobs`, `glassdoor.com`, `google.com`, `ziprecruiter.com`. |
| **`location`** | Search Box / Select | `str \| null` | `"remote"` | Set `"remote"` for remote-only. Set to a specific city/state (e.g. `"Cairo"`, `"San Francisco"`) for onsite/hybrid. Set to `""` or `null` for both. |
| **`countries`** | Multi-Select Dropdown | `list[str]` | `["usa"]` | Target countries. Case-insensitive; normalized by backend (e.g. `["egypt", "saudi arabia"]`). *Crucial for Indeed & Glassdoor searches.* |
| **`job_type`** | Select / Tabs | `str \| null` | `null` | Filters by type. Options: `full-time`, `part-time`, `internship`, `contract`. Synonyms are auto-mapped. |
| **`recent_hours`** | Select / Slider | `int \| null` | `24` | Post recency window in hours (e.g., `24` for last day, `72` for 3 days). Takes precedence over `days_back`. |
| **`days_back`** | Select / Dropdown | `int` | `1` | Recency filter in days (e.g. `1` or `3`). Used if `recent_hours` is not specified. |
| **`max_results`** | Number Input / Slider | `int` | `50` | Maximum results to retrieve *per job board* (range: `1` to `200`). |

### Advanced Filters (Toggles & Overrides)
| Parameter | UI Control | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`easy_apply`** | Toggle/Switch | `bool \| null` | `null` | If `true`, filters for single-click applications on LinkedIn and Indeed. |
| **`linkedin_fetch_description`** | Toggle/Switch | `bool` | `false` | If `true`, fetches full description & direct URL on LinkedIn. *Improves detail but increases load times.* |
| **`google_search_term`** | Text Input | `str \| null` | `null` | Direct search query override for Google Jobs. If empty, the backend auto-compiles an optimized term. |
| **`proxies`** | Text Area | `list[str] \| null`| `null` | Custom proxies list in `user:pass@host:port` format for rotating scraping IPs. |
| **`distance`** | Slider / Select | `int \| null` | `50` | Search radius in miles for local onsite searches. |
| **`enforce_annual_salary`** | Toggle/Switch | `bool \| null` | `null` | Converts all wage types (hourly, monthly) to annual salary figures. |
| **`description_format`** | Hidden / Advanced | `str` | `"markdown"` | Job description body format. Supported: `"markdown"`, `"html"`. |

---

## 2. Specific Search Use-Cases (API Request Payloads)

These exact payloads can be sent directly to `POST /search/jobspy` and are designed to solve specific user requirements:

### Use Case 1: Egypt, Onsite & Remote (Combined), Last 24 Hours
*   **Goal**: Find all "Software Engineer" or "DevOps" jobs in Egypt posted in the last 24 hours, including both work-from-home (remote) and local office (onsite) positions, from Indeed, LinkedIn, and Glassdoor.
*   **Payload**:
```json
{
  "keywords": ["software engineer", "devops"],
  "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "glassdoor.com"],
  "location": null,
  "countries": ["egypt"],
  "recent_hours": 24,
  "max_results": 30
}
```
> [!NOTE]
> Setting `"location": null` allows the scraper to retrieve both remote postings (which have location fields set to "Remote") and onsite postings located in Egypt.

---

### Use Case 2: Middle East, Remote, Last 24 Hours
*   **Goal**: Find all "Backend Engineer" or "Python" or "Go" jobs that are 100% remote, posted within the last 24 hours, across all supported Middle East countries.
*   **Payload**:
```json
{
  "keywords": ["backend engineer", "python", "go"],
  "job_sites": ["linkedin.com/jobs", "indeed.com/jobs", "google.com"],
  "location": "remote",
  "countries": ["egypt", "saudi arabia", "uae", "qatar", "kuwait", "bahrain", "oman"],
  "recent_hours": 24,
  "max_results": 40
}
```
> [!TIP]
> Indeed and Glassdoor support targeted local scrapers in the Middle East. Setting the `"countries"` array to multiple ME nations ensures JobSpy automatically routes searches through Indeed's corresponding local portals (`indeed.com.sa`, `ae.indeed.com`, etc.) to return maximum local remote roles.

---

### Use Case 3: Onsite/Local Specific Search (Cairo Office jobs within 25 miles)
*   **Goal**: Find "Frontend Developer" jobs located physically in Cairo within a 25-mile radius, from LinkedIn and Indeed.
*   **Payload**:
```json
{
  "keywords": ["frontend developer"],
  "job_sites": ["linkedin.com/jobs", "indeed.com/jobs"],
  "location": "Cairo",
  "countries": ["egypt"],
  "distance": 25,
  "recent_hours": 72,
  "max_results": 20
}
```

---

## 3. Normalized Output Mapping (Response Payload Schema)

The API returns a JSON array of flat objects. All values are guaranteed to be serialized safely (with all NaN/NaT fields converted to empty strings `""`). 

Each job object contains the following fields that your frontend can map to UI components:

```json
[
  {
    "id": "li-4417836167",
    "site": "linkedin",
    "job_url": "https://www.linkedin.com/jobs/view/4417836167",
    "job_url_direct": "https://company.careers/job/123",
    "title": "Software Engineer",
    "company": "Adobe",
    "location": "San Jose, CA, US",
    "date_posted": "2026-05-26",
    "job_type": "fulltime",
    "is_remote": true,
    "description": "Adobe is looking for...",
    
    "salary_source": "direct_data",
    "interval": "yearly",
    "min_amount": 120000.0,
    "max_amount": 160000.0,
    "currency": "USD",
    
    "company_industry": "Software",
    "company_url": "https://www.linkedin.com/company/adobe",
    "company_logo": "https://logo-url.png",
    "company_addresses": "San Jose, CA",
    "company_num_employees": "10,000+",
    "company_revenue": "$5B to $10B (USD)",
    "company_description": "Creative solutions..."
  }
]
```

### Key UI Mapping Guidelines for the Frontend

1.  **Platform Badges (`site`)**:
    Create distinct visual badges based on the `site` string:
    - `"linkedin"` -> Blue Badge
    - `"indeed"` -> Blue/Orange Indeed Badge
    - `"glassdoor"` -> Green Badge
    - `"google"` -> Multicolor Google Badge
    - `"zip_recruiter"` -> Green/Grey ZipRecruiter Badge
2.  **Salary Tags**:
    If `min_amount` and `max_amount` are populated, display them. Use `interval` and `currency` for clean formatting:
    - E.g., `120,000 USD - 160,000 USD / yr` or `$45 - $65 / hr` (if `interval` is `"hourly"`).
3.  **Apply Button (`job_url` vs `job_url_direct`)**:
    - Primary apply target: If `job_url_direct` is populated and not empty `""`, link the "Apply Now" button to `job_url_direct` (directs user to company ATS e.g. Greenhouse/Lever).
    - Secondary apply target: Fallback to the platform job page at `job_url`.
4.  **Remote Flag (`is_remote`)**:
    - Render a prominent "Remote" chip if `is_remote` is `true`.
5.  **Job Type Chip (`job_type`)**:
    - Display standard badges: `"fulltime"` -> `Full-Time`, `"parttime"` -> `Part-Time`, `"contract"` -> `Contract`, `"internship"` -> `Internship`.
6.  **Description Body (`description`)**:
    - Renders as Markdown by default. Use a Markdown rendering component (e.g. `react-markdown`) on the frontend to display styled bullet points, bold texts, and paragraphs.
