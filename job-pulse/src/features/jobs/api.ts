import type {
  FormState,
  PaginatedSearchResponse,
  CountriesResponse,
  SubAggregateResponse,
  CacheStatsResponse,
  ClearCacheResponse,
  DeleteOldJobsResponse,
} from "./types";

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

export async function postJobSearch(form: FormState, signal?: AbortSignal): Promise<PaginatedSearchResponse> {
  const base = getApiBase();
  const payload = {
    keywords: form.keywords,
    countries: form.countries,
    company: form.company || null,
    remote: form.remote,
    limit: form.limit,
    offset: form.offset,
  };

  const res = await fetch(`${base}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  const data = await res.json();
  return data as PaginatedSearchResponse;
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

export async function getCountries(signal?: AbortSignal): Promise<CountriesResponse> {
  const base = getApiBase();
  const res = await fetch(`${base}/search/countries`, { method: "GET", signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<CountriesResponse>;
}

export async function postSubAggregate(
  country: string,
  jobBoard: string,
  signal?: AbortSignal
): Promise<SubAggregateResponse> {
  const base = getApiBase();
  const res = await fetch(`${base}/search/aggregate/sub`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ country, job_board: jobBoard }),
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<SubAggregateResponse>;
}

export async function postAggregate(signal?: AbortSignal): Promise<{ status: string; message: string }> {
  const base = getApiBase();
  const res = await fetch(`${base}/search/aggregate`, { method: "POST", signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<{ status: string; message: string }>;
}

export async function getCacheStats(signal?: AbortSignal): Promise<CacheStatsResponse> {
  const base = getApiBase();
  const res = await fetch(`${base}/cache/stats`, { method: "GET", signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<CacheStatsResponse>;
}

export async function deleteCache(signal?: AbortSignal): Promise<ClearCacheResponse> {
  const base = getApiBase();
  const res = await fetch(`${base}/cache`, { method: "DELETE", signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<ClearCacheResponse>;
}

export interface DeleteOldJobsParams {
  days?: number;
  hours?: number;
  minutes?: number;
  start_date?: string;
  end_date?: string;
  truncate?: boolean;
}

export async function deleteOldJobs(
  params: DeleteOldJobsParams,
  signal?: AbortSignal
): Promise<DeleteOldJobsResponse> {
  const base = getApiBase();
  const url = new URL(`${base}/jobs/old`);
  
  if (params.days !== undefined) url.searchParams.append("days", params.days.toString());
  if (params.hours !== undefined) url.searchParams.append("hours", params.hours.toString());
  if (params.minutes !== undefined) url.searchParams.append("minutes", params.minutes.toString());
  if (params.start_date) url.searchParams.append("start_date", params.start_date);
  if (params.end_date) url.searchParams.append("end_date", params.end_date);
  if (params.truncate !== undefined) url.searchParams.append("truncate", params.truncate.toString());

  const res = await fetch(url.toString(), { method: "DELETE", signal });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<DeleteOldJobsResponse>;
}


