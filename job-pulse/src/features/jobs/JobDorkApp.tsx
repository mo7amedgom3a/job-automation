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
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setError(e?.message ?? String(e));
      setStatus("error");
    }
  }, [form]);

  const applyPreset = useCallback((patch: Partial<FormState>) => {
    setForm((f) => ({ ...f, ...patch }));
  }, []);

  // Derived: filtered + sorted
  const visible = useMemo(() => {
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
    let out = results.filter((r) => {
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
  }, [results, filters, sort]);

  // Active filter pills (from form + client filters)
  const activePills = useMemo(() => {
    const pills: { id: string; label: string; remove: () => void }[] = [];
    form.keywords.forEach((k) => pills.push({ id: `kw-${k}`, label: k, remove: () => patchForm({ keywords: form.keywords.filter((x) => x !== k) }) }));
    form.countries.forEach((c) => pills.push({ id: `co-${c}`, label: c, remove: () => patchForm({ countries: form.countries.filter((x) => x !== c) }) }));
    if (form.workType === "remote") pills.push({ id: "wt", label: "Remote", remove: () => patchForm({ workType: "both" }) });
    if (form.workType === "onsite" && form.onsiteCity) pills.push({ id: "wt", label: `Onsite · ${form.onsiteCity}`, remove: () => patchForm({ workType: "both", onsiteCity: "" }) });
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
