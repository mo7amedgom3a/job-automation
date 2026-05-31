import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./jobdork.css";
import type { FormState, JobResult, SiteId } from "./types";
import { buildPayload, postJobSearch } from "./api";
import { PRESETS } from "./presets";
import { isEmpty, SITE_LABEL } from "./utils";
import { TopNav } from "./components/TopNav";
import { SearchForm } from "./components/SearchForm";
import { JobCard } from "./components/JobCard";
import { SkeletonGrid } from "./components/SkeletonGrid";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { FilterSidebar, type ClientFilters } from "./components/FilterSidebar";
import linkedinIcon from "@/asset/linkedin.svg";
import indeedIcon from "@/asset/indeed.svg";

const INITIAL: FormState = {
  keywords: [],
  jobSites: ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"],
  workType: "remote",
  onsiteCity: "",
  jobType: "any",
  countries: ["usa"],
  postedWithin: "24h",
  maxResults: 30,
  easyApply: false,
  strictCountry: false,
  linkedinFetchDescription: false,
  distance: 25,
  enforceAnnualSalary: false,
  googleSearchTerm: "",
};

const EMPTY_FILTERS: ClientFilters = {
  companies: [], locations: [], remoteOnly: false, levels: [], functions: [], salary: null,
};

type Status = "idle" | "loading" | "success" | "error";
type Sort = "date" | "salary" | "company";

export function JobDorkApp() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<JobResult[]>([]);
  const [error, setError] = useState("");
  const [layout, setLayout] = useState<"grid" | "list">("grid");
  const [sort, setSort] = useState<Sort>("date");
  const [filters, setFilters] = useState<ClientFilters>(EMPTY_FILTERS);
  const [view, setView] = useState<"search" | "results">("search");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [activeSourceTab, setActiveSourceTab] = useState<"all" | "linkedin" | "indeed" | "google">("all");
  const ctrlRef = useRef<AbortController | null>(null);

  const patchForm = useCallback((p: Partial<FormState>) => setForm((f) => ({ ...f, ...p })), []);
  const patchFilters = useCallback((p: Partial<ClientFilters>) => setFilters((f) => ({ ...f, ...p })), []);

  const runSearch = useCallback(async () => {
    if (!form.keywords.length) return;
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setStatus("loading");
    setError("");
    setView("results");
    setFilters(EMPTY_FILTERS);
    try {
      const data = await postJobSearch(buildPayload(form), ctrl.signal);
      if (ctrl.signal.aborted) return;
      setResults(data);
      setStatus("success");
      setActiveSourceTab("all");
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }, [form]);

  const applyPreset = useCallback((patch: Partial<FormState>) => {
    setForm((f) => ({ ...f, ...patch }));
  }, []);

  // Derived: filtered + sorted
  // Derived: filtered by sidebar criteria (pre-source-tab filtering)
  const filteredBySidebar = useMemo(() => {
    const COUNTRY_ALIASES: Record<string, string[]> = {
      egypt: ["egypt", "eg", "cairo", "giza", "alexandria"],
      usa: ["usa", "us", "united states", "america"],
      us: ["usa", "us", "united states", "america"],
      "united kingdom": ["uk", "gb", "united kingdom", "london", "great britain"],
      uk: ["uk", "gb", "united kingdom", "london", "great britain"],
      germany: ["germany", "de", "deutschland", "berlin", "munich"],
      france: ["france", "fr", "paris"],
      canada: ["canada", "ca", "toronto", "vancouver", "montreal"],
      australia: ["australia", "au", "sydney", "melbourne"],
      "saudi arabia": ["saudi arabia", "sa", "riyadh", "jeddah"],
      uae: ["uae", "ae", "united arab emirates", "dubai", "abu dhabi"],
      "united arab emirates": ["uae", "ae", "united arab emirates", "dubai", "abu dhabi"],
      qatar: ["qatar", "qa", "doha"],
      kuwait: ["kuwait", "kw"],
      bahrain: ["bahrain", "bh", "manama"],
      oman: ["oman", "om", "muscat"],
    };

    const toN = (x: string | number) => {
      if (typeof x === "number") return isNaN(x) ? 0 : x;
      const n = parseFloat((x || "").toString().replace(/[,\s]/g, ""));
      return isNaN(n) ? 0 : n;
    };

    return results.filter((r) => {
      const blacklist = [
        "crossing hurdles", "turing", "confidential", "confidential careers",
        "micro1", "canonical", "naphora games group", "meridial marketplace",
        "by invisible", "invisible", "siira", "proxify", "dataannotation",
        "mindrift", "mercor", "Jobgether"
      ];
      const compLower = (r.company || "").toLowerCase().trim();
      if (blacklist.some((scam) => compLower.includes(scam))) return false;

      if (form.strictCountry && form.countries.length > 0) {
        const loc = (r.location || "").toLowerCase();
        const compAddr = (r.company_addresses || "").toLowerCase();
        const matches = form.countries.some((c) => {
          const aliases = COUNTRY_ALIASES[c.toLowerCase()];
          if (aliases) return aliases.some((a) => loc.includes(a) || compAddr.includes(a));
          return loc.includes(c.toLowerCase()) || compAddr.includes(c.toLowerCase());
        });
        if (!matches) return false;
      }
      if (filters.remoteOnly && !r.is_remote) return false;
      if (filters.companies.length && !filters.companies.includes(r.company)) return false;
      if (filters.locations.length && !filters.locations.includes(r.location)) return false;
      if (filters.levels.length && !filters.levels.includes(r.job_level)) return false;
      if (filters.functions.length && !filters.functions.includes(r.job_function)) return false;
      if (filters.salary) {
        const mn = toN(r.min_amount); const mx = toN(r.max_amount);
        const rep = mx || mn;
        if (rep && (rep < filters.salary[0] || rep > filters.salary[1])) return false;
      }
      return true;
    });
  }, [results, filters, form.strictCountry, form.countries]);

  // Derived: counts for each source tab based on sidebar-filtered results
  const tabCounts = useMemo(() => {
    let linkedin = 0;
    let indeed = 0;
    let google = 0;

    filteredBySidebar.forEach((r) => {
      const site = (r.site || "").toLowerCase();
      if (site === "linkedin") linkedin++;
      else if (site === "indeed") indeed++;
      else google++;
    });

    return {
      all: filteredBySidebar.length,
      linkedin,
      indeed,
      google,
    };
  }, [filteredBySidebar]);

  // Derived: fully filtered + sorted for display
  const visible = useMemo(() => {
    let out = filteredBySidebar;

    if (activeSourceTab === "linkedin") {
      out = out.filter((r) => (r.site || "").toLowerCase() === "linkedin");
    } else if (activeSourceTab === "indeed") {
      out = out.filter((r) => (r.site || "").toLowerCase() === "indeed");
    } else if (activeSourceTab === "google") {
      out = out.filter((r) => {
        const site = (r.site || "").toLowerCase();
        return site !== "linkedin" && site !== "indeed";
      });
    }

    const toN = (x: string | number) => {
      if (typeof x === "number") return isNaN(x) ? 0 : x;
      const n = parseFloat((x || "").toString().replace(/[,\s]/g, ""));
      return isNaN(n) ? 0 : n;
    };

    if (sort === "date") {
      out = [...out].sort((a, b) => {
        const da = a.date_posted ? new Date(a.date_posted).getTime() : 0;
        const db = b.date_posted ? new Date(b.date_posted).getTime() : 0;
        return db - da;
      });
    } else if (sort === "salary") {
      out = [...out].sort((a, b) => Math.max(toN(a.max_amount), toN(a.min_amount)) < Math.max(toN(b.max_amount), toN(b.min_amount)) ? 1 : -1);
    } else if (sort === "company") {
      out = [...out].sort((a, b) => (a.company || "").localeCompare(b.company || ""));
    }
    return out;
  }, [filteredBySidebar, activeSourceTab, sort]);

  // Active filter pills (from form + client filters)
  const activePills = useMemo(() => {
    const pills: { id: string; label: string; remove: () => void }[] = [];
    form.keywords.forEach((k) => pills.push({ id: `kw-${k}`, label: k, remove: () => patchForm({ keywords: form.keywords.filter((x) => x !== k) }) }));
    form.countries.forEach((c) => pills.push({ id: `co-${c}`, label: c, remove: () => patchForm({ countries: form.countries.filter((x) => x !== c) }) }));
    if (form.workType === "onsite" && form.onsiteCity) pills.push({ id: "wt", label: `Onsite · ${form.onsiteCity}`, remove: () => patchForm({ onsiteCity: "" }) });
    if (form.jobType !== "any") pills.push({ id: "jt", label: form.jobType, remove: () => patchForm({ jobType: "any" }) });
    pills.push({ id: "pw", label: { "24h": "Last 24h", "3d": "Last 3d", "7d": "Last 7d", "30d": "Last 30d" }[form.postedWithin], remove: () => patchForm({ postedWithin: "30d" }) });
    form.jobSites.forEach((s: SiteId) => pills.push({ id: `s-${s}`, label: SITE_LABEL[s], remove: () => patchForm({ jobSites: form.jobSites.filter((x) => x !== s) }) }));
    filters.companies.forEach((c) => pills.push({ id: `fc-${c}`, label: c, remove: () => patchFilters({ companies: filters.companies.filter((x) => x !== c) }) }));
    filters.locations.forEach((c) => pills.push({ id: `fl-${c}`, label: c, remove: () => patchFilters({ locations: filters.locations.filter((x) => x !== c) }) }));
    if (filters.remoteOnly) pills.push({ id: "fro", label: "Remote only", remove: () => patchFilters({ remoteOnly: false }) });
    if (form.strictCountry) pills.push({ id: "sc", label: "Strict Country Filter", remove: () => patchForm({ strictCountry: false }) });
    return pills;
  }, [form, filters, patchForm, patchFilters]);

  useEffect(() => () => ctrlRef.current?.abort(), []);

  return (
    <div className="jobdork">
      <TopNav />
      {status === "loading" && <div className="jd-progress" />}

      {view === "search" ? (
        <>
          <div className="jd-hero">
            <h1>Find your next role.</h1>
            <p className="sub">
              Scraping <b>LinkedIn</b> · <b>Indeed</b> · <b>Glassdoor</b> · <b>Google Jobs</b> · <b>ZipRecruiter</b> — simultaneously.
            </p>
          </div>
          <div className="jd-form">
            <SearchForm value={form} onChange={patchForm} onSubmit={runSearch} loading={status === "loading"} />
            <div className="jd-presets">
              {PRESETS.map((p) => (
                <button key={p.id} className="jd-preset" onClick={() => applyPreset(p.patch)}>{p.label}</button>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="jd-results">
          <aside className="jd-sidebar">
            <div className="jd-panel">
              <h4>Active search</h4>
              <ul className="jd-summary-list">
                <li><b>{form.keywords.join(", ") || "—"}</b></li>
                <li>{form.workType === "remote" ? "Remote" : form.workType === "onsite" ? `Onsite · ${form.onsiteCity || "—"}` : "Remote + Onsite"}</li>
                <li>{form.countries.join(", ")}</li>
                <li>Platforms: {form.jobSites.length}</li>
              </ul>
              <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
                <button className="jd-btn ghost" onClick={() => setView("search")}>Edit</button>
                <button className="jd-btn" onClick={() => { setForm(INITIAL); setResults([]); setStatus("idle"); setView("search"); }}>New Search</button>
              </div>
            </div>
            <FilterSidebar results={results} filters={filters} onChange={patchFilters} />
          </aside>

          <main>
            <div className="jd-source-tabs">
              <button
                type="button"
                className={`jd-source-tab-btn ${activeSourceTab === "all" ? "active" : ""}`}
                onClick={() => setActiveSourceTab("all")}
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="jd-tab-icon">
                  <rect x="3" y="3" width="7" height="7" />
                  <rect x="14" y="3" width="7" height="7" />
                  <rect x="14" y="14" width="7" height="7" />
                  <rect x="3" y="14" width="7" height="7" />
                </svg>
                <span>All Jobs</span>
                <span className="jd-tab-badge">{tabCounts.all}</span>
              </button>
              
              <button
                type="button"
                className={`jd-source-tab-btn ${activeSourceTab === "linkedin" ? "active" : ""}`}
                onClick={() => setActiveSourceTab("linkedin")}
              >
                <img src={linkedinIcon} className="jd-tab-icon" alt="" />
                <span>LinkedIn</span>
                <span className="jd-tab-badge">{tabCounts.linkedin}</span>
              </button>
              
              <button
                type="button"
                className={`jd-source-tab-btn ${activeSourceTab === "indeed" ? "active" : ""}`}
                onClick={() => setActiveSourceTab("indeed")}
              >
                <img src={indeedIcon} className="jd-tab-icon" alt="" />
                <span>Indeed</span>
                <span className="jd-tab-badge">{tabCounts.indeed}</span>
              </button>
              
              <button
                type="button"
                className={`jd-source-tab-btn ${activeSourceTab === "google" ? "active" : ""}`}
                onClick={() => setActiveSourceTab("google")}
              >
                <svg viewBox="0 0 24 24" width="14" height="14" className="jd-tab-icon">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22c-.87-2.6-3.3-4.53-6.16-4.53z" />
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
                <span>Google Jobs</span>
                <span className="jd-tab-badge">{tabCounts.google}</span>
              </button>
            </div>

            <div className="jd-toolbar">
              <div className="count" aria-live="polite">
                {status === "loading" ? <span>Searching…</span> : <><b>{visible.length}</b>jobs found{visible.length !== results.length ? ` of ${results.length}` : ""}</>}
              </div>
              <div className="spacer" />
              <div className="jd-view-toggle">
                <button className={layout === "grid" ? "active" : ""} onClick={() => setLayout("grid")} title="Grid">▦</button>
                <button className={layout === "list" ? "active" : ""} onClick={() => setLayout("list")} title="List">≡</button>
              </div>
              <select className="jd-select mono" style={{ width: "auto" }} value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                <option value="date">Date Posted</option>
                <option value="salary">Salary (high→low)</option>
                <option value="company">Company (A→Z)</option>
              </select>
            </div>

            {activePills.length > 0 && (
              <div className="jd-active-filters">
                {activePills.map((p) => (
                  <button key={p.id + p.label} className="jd-filter-pill" onClick={p.remove}>× {p.label}</button>
                ))}
                <button className="jd-filter-clear" onClick={() => { setForm({ ...INITIAL, keywords: [] }); setFilters(EMPTY_FILTERS); }}>Clear all</button>
              </div>
            )}

            {status === "loading" && <SkeletonGrid layout={layout} />}
            {status === "error" && <ErrorState message={error} onRetry={runSearch} />}
            {status === "success" && visible.length === 0 && <EmptyState onAdjust={() => setView("search")} />}
            {status === "success" && visible.length > 0 && (
              <div className={`jd-cards ${layout}`}>
                {visible.map((j, i) => (
                  <JobCard key={`${j.site}-${j.id}-${i}`} job={j} index={i} layout={layout} />
                ))}
              </div>
            )}
          </main>

          <button className="jd-fab" onClick={() => setDrawerOpen(true)}>Filters</button>
          {drawerOpen && (
            <>
              <div className="jd-drawer-bd" onClick={() => setDrawerOpen(false)} />
              <div className="jd-drawer">
                <button className="jd-btn close" onClick={() => setDrawerOpen(false)}>Close</button>
                <h3 style={{ margin: "4px 0 16px", fontFamily: "Sora" }}>Filters</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <FilterSidebar results={results} filters={filters} onChange={patchFilters} />
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// silence unused import warning if isEmpty referenced elsewhere
void isEmpty;
