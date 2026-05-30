import type { FormState, JobResult, PostedWithinKey, SearchPayload } from "./types";
import { SITE_DOMAIN } from "./utils";

const STORAGE_KEY = "jobdork_api_base";
const DEFAULT_BASE = "http://127.0.0.1:8000";

export function getApiBase(): string {
  if (typeof window === "undefined") return DEFAULT_BASE;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "http://localhost:8000") return DEFAULT_BASE;
  return stored || DEFAULT_BASE;
}

export function setApiBase(v: string) {
  if (typeof window === "undefined") return;
  if (v) window.localStorage.setItem(STORAGE_KEY, v.replace(/\/$/, ""));
  else window.localStorage.removeItem(STORAGE_KEY);
}

function postedWithinToTime(k: PostedWithinKey): { recent_hours: number | null; days_back: number | null } {
  switch (k) {
    case "24h": return { recent_hours: 24, days_back: null };
    case "3d": return { recent_hours: 72, days_back: null };
    case "7d": return { recent_hours: null, days_back: 7 };
    case "30d": return { recent_hours: null, days_back: 30 };
  }
}

export function buildPayload(f: FormState): SearchPayload {
  const time = postedWithinToTime(f.postedWithin);
  let location: string | null;
  if (f.workType === "remote") location = "remote";
  else if (f.workType === "onsite") location = f.onsiteCity.trim() || null;
  else location = null;

  return {
    keywords: f.keywords,
    job_sites: f.jobSites.map((s) => SITE_DOMAIN[s] ?? s),
    location,
    countries: f.countries,
    job_type: f.jobType === "any" ? null : f.jobType,
    recent_hours: time.recent_hours,
    days_back: time.days_back,
    max_results: f.maxResults,
    easy_apply: f.easyApply ? true : null,
    strict_country: f.strictCountry ? true : null,
    linkedin_fetch_description: f.linkedinFetchDescription,
    distance: f.workType === "onsite" ? f.distance : null,
    enforce_annual_salary: f.enforceAnnualSalary ? true : null,
    google_search_term: f.googleSearchTerm.trim() || null,
  };
}

export async function postJobSearch(payload: SearchPayload, signal?: AbortSignal): Promise<JobResult[]> {
  const base = getApiBase();
  // Strip null and undefined values so that Pydantic on the backend uses the defined default values instead of failing validations
  const cleanPayload = Object.fromEntries(
    Object.entries(payload).filter(([_, v]) => v !== null && v !== undefined)
  );

  const res = await fetch(`${base}/search/orchestrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  const data = await res.json();
  
  // If it is the orchestrated response object { linkedin, indeed, google }
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const flattened: JobResult[] = [];
    
    if (Array.isArray(data.linkedin)) {
      data.linkedin.forEach((j: any) => {
        j.site = "linkedin";
        flattened.push(j);
      });
    }
    
    if (Array.isArray(data.indeed)) {
      data.indeed.forEach((j: any) => {
        j.site = "indeed";
        flattened.push(j);
      });
    }
    
    if (Array.isArray(data.google)) {
      data.google.forEach((j: any) => {
        // Map backend parser keys to frontend JobResult fields
        j.job_url = j.job_url || j.url || "";
        j.date_posted = j.date_posted || j.posted_at || "";
        j.site = j.site || j.source || "google";
        j.is_remote = j.is_remote || (j.location && j.location.toLowerCase().includes("remote")) || false;
        
        // Try parsing salary strings into min/max numbers for filters
        if (j.salary && !j.max_amount && !j.min_amount) {
          const salMatch = j.salary.match(/\d+/g);
          if (salMatch && salMatch.length >= 2) {
            j.min_amount = parseInt(salMatch[0]);
            j.max_amount = parseInt(salMatch[1]);
          } else if (salMatch && salMatch.length === 1) {
            j.min_amount = parseInt(salMatch[0]);
          }
        }
        
        flattened.push(j);
      });
    }
    
    return flattened;
  }
  
  if (Array.isArray(data)) return data as JobResult[];
  if (data && Array.isArray((data as any).results)) return (data as any).results as JobResult[];
  if (data && Array.isArray((data as any).jobs)) return (data as any).jobs as JobResult[];
  return [];
}

export async function pingApi(signal?: AbortSignal): Promise<boolean> {
  const base = getApiBase();
  try {
    const res = await fetch(`${base}/health`, { method: "GET", signal });
    return res.ok;
  } catch {
    return false;
  }
}
