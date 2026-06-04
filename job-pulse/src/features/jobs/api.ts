import type { FormState, PaginatedSearchResponse } from "./types";

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
