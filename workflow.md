This document outlines the architecture and execution flow for your automated job aggregation engine. It combines decentralized web scraping via a custom Python microservice with an n8n orchestration pipeline and AI-driven semantic filtering.
1. Target Profile Configuration

The search parameters and AI prompt are calibrated for a versatile software engineer bridging full-stack, backend, DevOps, and cloud-native domains.

    Target Job Titles: Backend Engineer, DevOps Engineer, Cloud Architect, Full Stack Engineer, Platform Engineer, Vibe coder, Frotend Engineer

    Core Keywords: AWS, Terraform, Serverless, Go (Golang), Python (FastAPI), React, Cloudflare Workers, CI/CD, Kubernetes.

    Job Types: Remote, Contract, Full-time.

    Target Geographies: Egypt(onsite, hybrid, remote), Worldwide (Remote), USA(remote), Canada(remote), UK(remote), Europe, MENA/Egypt (for timezone-aligned remote roles).

2. Search Strategy (Advanced Dorking)

Instead of fighting the anti-bot measures of major job boards, the system queries Applicant Tracking Systems (ATS) directly using the DuckDuckGo microservice.

Primary ATS Dorks (To be passed to the FastAPI microservice):

    site:boards.greenhouse.io ("DevOps" OR "Backend" OR "Full Stack") ("Go" OR "Python" OR "AWS") "Remote"

    site:jobs.lever.co ("Cloud Engineer" OR "Platform Engineer") ("Terraform" OR "Serverless") "Remote"

    site:jobs.ashbyhq.com ("Backend" OR "DevOps") ("FastAPI" OR "React") "Remote"

3. Workflow Execution Steps
Step 1: Initialization & Configuration (n8n)

    Cron Trigger: The pipeline executes on a scheduled interval (e.g., every 6 hours).

    State Sync: The workflow immediately queries the connected Google Sheet (Blocklist tab) to cache the latest arrays of blocked_companies, blocked_keywords, and scam_phrases.

Step 2: Data Ingestion (FastAPI Microservice)

    Execution: n8n sends HTTP GET requests to your custom Python FastAPI service (http://scraper-api:8000/search).

    Scraping: The microservice utilizes the duckduckgo-search library to execute the ATS Dorks, bypassing standard rate limits and returning raw, unformatted search results in JSON format.

Step 3: Normalization & Deduplication (n8n)

    Schema Mapping: An n8n Code node extracts the href, title, and body (snippet) from the DuckDuckGo response. It standardizes these into a uniform job schema.

    Hashing: A unique MD5 hash is generated from the job URL.

    Local State Check: The hash is checked against the local SQLite database (seen_jobs table). If the hash exists, the job is immediately dropped to prevent downstream redundancy.

Step 4: Pre-Computation Filtering (n8n)

    Deterministic Blocklist Check: Before spending AI tokens, an n8n Code node compares the job string (title + company + description snippet) against the Google Sheets arrays.

    Action: If a match is found (e.g., an MLM keyword or a blocked company), the job is routed to the Log Blocked to Sheet node and discarded.

Step 5: AI Semantic Enrichment & Scoring

    LLM Processing: The surviving, unique jobs are sent via an HTTP Request node to OpenRouter, targeting the gpt-oss-120b model.

    System Prompt: The LLM evaluates the job against your specific engineering profile and the dynamic scam list.

LLM Execution Prompt:
Plaintext

You are a technical recruiter evaluating roles for a multidisciplinary Software Engineer (DevOps, Backend, Full-Stack). 
Analyze this job posting.

Title: {{ $json.title }}
Description Snippet: {{ $json.description }}

Check against these scam patterns from our live sheet:
{{ $('Build Blocklist Arrays').first().json.scamKeywords.join(', ') }}

Return ONLY valid JSON:
{
  "is_scam": false,
  "scam_reason": "",
  "relevance_score": 8,
  "relevance_reason": "Matches Go, AWS, and Serverless experience.",
  "job_type": "full-time",
  "remote": true,
  "detected_skills": ["AWS", "Terraform", "Go"]
}

Step 6: Quality Gate & Delivery

    Logic Gate: An n8n IF node filters out any jobs where ai_is_scam === true or ai_relevance_score < 7.

    Telegram Notification: High-value jobs are formatted with HTML tags and sent to your Telegram bot, displaying the title, detected skills, relevance reason, and the direct ATS link.

    Database Commit: The job ID is inserted into the SQLite seen_jobs table, and any AI-flagged scams are appended to the Scam Log tab in your Google Sheet for continuous tuning of your blocklist.