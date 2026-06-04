import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import "./jobdork.css";
import type { FormState, Job, CountryGroup } from "./types";
import { postJobSearch } from "./api";
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
  countries: [],
  company: null,
  remote: null,
  limit: 50,
  offset: 0,
};

const EMPTY_FILTERS: ClientFilters = {
  companies: [],
  locations: [],
  remoteOnly: false,
  tags: [],
};

const COUNTRY_FLAGS: Record<string, string> = {
  egypt: "🇪🇬",
  usa: "🇺🇸",
  "saudi arabia": "🇸🇦",
  uae: "🇦🇪",
  qatar: "🇶🇦",
  kuwait: "🇰🇼",
  bahrain: "🇧🇭",
  oman: "🇴🇲",
  uk: "🇬🇧",
  germany: "🇩🇪",
  canada: "🇨🇦",
  france: "🇫🇷",
};

type Status = "idle" | "loading" | "success" | "error";
type Sort = "date" | "company";

export function JobDorkApp() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<CountryGroup[]>([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [error, setError] = useState("");
  const [layout, setLayout] = useState<"grid" | "list">("grid");
  const [sort, setSort] = useState<Sort>("date");
  const [filters, setFilters] = useState<ClientFilters>(EMPTY_FILTERS);
  const [view, setView] = useState<"search" | "results">("search");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const ctrlRef = useRef<AbortController | null>(null);

  const patchForm = useCallback((p: Partial<FormState>) => setForm((f) => ({ ...f, ...p })), []);
  const patchFilters = useCallback((p: Partial<ClientFilters>) => setFilters((f) => ({ ...f, ...p })), []);

  const runSearch = useCallback(async (currentForm: FormState = form) => {
    if (!currentForm.keywords.length) return;
    ctrlRef.current?.abort();
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    setStatus("loading");
    setError("");
    setView("results");
    if (currentForm.offset === 0) {
      setFilters(EMPTY_FILTERS);
    }
    try {
      const data = await postJobSearch(currentForm, ctrl.signal);
      if (ctrl.signal.aborted) return;
      
      let parsedResults: CountryGroup[] = [];
      let total = 0;
      
      if (data && typeof data === "object") {
        if ("results" in data && Array.isArray(data.results)) {
          parsedResults = data.results;
          total = typeof data.total === "number" ? data.total : 0;
        } else if (Array.isArray(data)) {
          parsedResults = data;
          total = data.reduce((acc, cg) => acc + (cg.job_boards?.reduce((acc2, jb) => acc2 + (jb.jobs?.length || 0), 0) || 0), 0);
        }
      }
      
      setResults(parsedResults);
      setTotalJobs(total);
      setStatus("success");
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : String(e));
      setStatus("error");
    }
  }, [form]);


  const handleSearchSubmit = useCallback(() => {
    const updated = { ...form, offset: 0 };
    setForm(updated);
    runSearch(updated);
  }, [form, runSearch]);

  const handlePageChange = useCallback((newOffset: number) => {
    const updated = { ...form, offset: newOffset };
    setForm(updated);
    runSearch(updated);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [form, runSearch]);

  const applyPreset = useCallback((patch: Partial<FormState>) => {
    const updated = { ...INITIAL, ...patch, offset: 0 };
    setForm(updated);
    runSearch(updated);
  }, [runSearch]);


  // Derived: Flattened jobs list from CountryGroups response
  const allJobs = useMemo(() => {
    const list: Job[] = [];
    if (!Array.isArray(results)) return list;
    results.forEach((cg) => {
      if (cg && Array.isArray(cg.job_boards)) {
        cg.job_boards.forEach((jb) => {
          if (jb && Array.isArray(jb.jobs)) {
            jb.jobs.forEach((j) => {
              list.push({
                ...j,
                site: jb.name, // Ensure job site is set correctly
              });
            });
          }
        });
      }
    });
    return list;
  }, [results]);

  // Derived: filtered jobs by sidebar criteria
  const filteredBySidebar = useMemo(() => {
    const blacklist = [
      "crossing hurdles", "turing", "confidential", "confidential careers",
      "micro1", "canonical", "naphora games group", "meridial marketplace",
      "by invisible", "invisible", "siira", "proxify", "dataannotation",
      "mindrift", "mercor", "Jobgether"
    ];

    return allJobs.filter((r) => {
      const compLower = (r.company || "").toLowerCase().trim();
      if (blacklist.some((scam) => compLower.includes(scam))) return false;

      if (filters.remoteOnly && !(r.location?.toLowerCase().includes("remote") || r.is_remote)) return false;
      if (filters.companies.length && !filters.companies.includes(r.company)) return false;
      if (filters.locations.length && !filters.locations.includes(r.location)) return false;
      if (filters.tags.length && !filters.tags.some((t) => r.tags?.includes(t))) return false;

      return true;
    });
  }, [allJobs, filters]);

  // Derived: fully filtered + sorted for display
  const visible = useMemo(() => {
    let out = [...filteredBySidebar];

    if (sort === "date") {
      out.sort((a, b) => {
        const da = a.scraped_at ? new Date(a.scraped_at).getTime() : 0;
        const db = b.scraped_at ? new Date(b.scraped_at).getTime() : 0;
        return db - da;
      });
    } else if (sort === "company") {
      out.sort((a, b) => (a.company || "").localeCompare(b.company || ""));
    }
    return out;
  }, [filteredBySidebar, sort]);

  // Re-group visible jobs to show Country -> Job Board nested rendering
  const groupedVisible = useMemo(() => {
    const visibleIds = new Set(visible.map((j) => j.id));
    const groups: CountryGroup[] = [];

    results.forEach((cg) => {
      const matchedBoards = cg.job_boards
        .map((jb) => {
          const matchedJobs = jb.jobs.filter((j) => visibleIds.has(j.id));
          const sortedJobs = [...matchedJobs];
          if (sort === "date") {
            sortedJobs.sort((a, b) => {
              const da = a.scraped_at ? new Date(a.scraped_at).getTime() : 0;
              const db = b.scraped_at ? new Date(b.scraped_at).getTime() : 0;
              return db - da;
            });
          } else if (sort === "company") {
            sortedJobs.sort((a, b) => (a.company || "").localeCompare(b.company || ""));
          }
          return {
            ...jb,
            jobs: sortedJobs,
          };
        })
        .filter((jb) => jb.jobs.length > 0);

      if (matchedBoards.length > 0) {
        groups.push({
          ...cg,
          job_boards: matchedBoards,
        });
      }
    });

    const getCountryPriority = (name: string): number => {
      const norm = name.toLowerCase().trim();
      if (norm === "egypt" || norm === "eg") return 1;

      const arab = [
        "saudi arabia", "saudi", "sa", "united arab emirates", "uae", "ae", "qatar", "qa",
        "kuwait", "kw", "bahrain", "bh", "oman", "om", "jordan", "jo", "lebanon", "lb",
        "iraq", "iq", "morocco", "ma", "algeria", "dz", "tunisia", "tn"
      ];
      if (arab.includes(norm)) return 2;

      const europe = [
        "united kingdom", "uk", "gb", "england", "germany", "de", "deutschland",
        "france", "fr", "poland", "pl", "spain", "es", "italy", "it", "netherlands", "nl",
        "sweden", "se", "switzerland", "ch", "ireland", "ie", "belgium", "be", "austria", "at"
      ];
      if (europe.includes(norm)) return 3;

      if (norm === "canada" || norm === "ca") return 4;

      return 5;
    };

    groups.sort((a, b) => {
      const prioA = getCountryPriority(a.country);
      const prioB = getCountryPriority(b.country);
      if (prioA !== prioB) return prioA - prioB;
      return a.country.localeCompare(b.country);
    });

    return groups;
  }, [results, visible, sort]);

  // Active filter pills
  const activePills = useMemo(() => {
    const pills: { id: string; label: string; remove: () => void }[] = [];
    form.keywords.forEach((k) =>
      pills.push({
        id: `kw-${k}`,
        label: k,
        remove: () => patchForm({ keywords: form.keywords.filter((x) => x !== k) }),
      })
    );
    form.countries.forEach((c) =>
      pills.push({
        id: `co-${c}`,
        label: c,
        remove: () => patchForm({ countries: form.countries.filter((x) => x !== c) }),
      })
    );
    if (form.company) {
      pills.push({
        id: "comp",
        label: `Company: ${form.company}`,
        remove: () => patchForm({ company: null }),
      });
    }
    if (form.remote !== null) {
      pills.push({
        id: "rem",
        label: form.remote ? "Remote only" : "Onsite/Hybrid only",
        remove: () => patchForm({ remote: null }),
      });
    }

    filters.companies.forEach((c) =>
      pills.push({
        id: `fc-${c}`,
        label: c,
        remove: () => patchFilters({ companies: filters.companies.filter((x) => x !== c) }),
      })
    );
    filters.locations.forEach((l) =>
      pills.push({
        id: `fl-${l}`,
        label: l,
        remove: () => patchFilters({ locations: filters.locations.filter((x) => x !== l) }),
      })
    );
    filters.tags.forEach((t) =>
      pills.push({
        id: `ft-${t}`,
        label: t,
        remove: () => patchFilters({ tags: filters.tags.filter((x) => x !== t) }),
      })
    );
    if (filters.remoteOnly) {
      pills.push({
        id: "fro",
        label: "Remote only (local)",
        remove: () => patchFilters({ remoteOnly: false }),
      });
    }
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
              Scraping global job boards and search dorks — simultaneously.
            </p>
          </div>
          <div className="jd-form">
            <SearchForm value={form} onChange={patchForm} onSubmit={handleSearchSubmit} loading={status === "loading"} />
            <div className="jd-presets">
              {PRESETS.map((p) => (
                <button key={p.id} className="jd-preset" onClick={() => applyPreset(p.patch)}>
                  {p.label}
                </button>
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
                <li>
                  <b>{form.keywords.join(", ") || "—"}</b>
                </li>
                <li>
                  Location type: {form.remote === null ? "Any" : form.remote ? "Remote Only" : "Onsite/Hybrid"}
                </li>
                {form.countries.length > 0 && <li>Countries: {form.countries.join(", ")}</li>}
                {form.company && <li>Company: {form.company}</li>}
              </ul>
              <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
                <button className="jd-btn ghost" onClick={() => setView("search")}>
                  Edit
                </button>
                <button
                  className="jd-btn"
                  onClick={() => {
                    setForm(INITIAL);
                    setResults([]);
                    setStatus("idle");
                    setView("search");
                  }}
                >
                  New Search
                </button>
              </div>
            </div>
            <FilterSidebar results={allJobs} filters={filters} onChange={patchFilters} />
          </aside>

          <main>
            <div className="jd-toolbar">
              <div className="count" aria-live="polite">
                {status === "loading" ? (
                  <span>Searching…</span>
                ) : (
                  <>
                    Showing <b>{visible.length}</b> of <b>{totalJobs}</b> jobs found
                  </>
                )}
              </div>
              <div className="spacer" />
              <div className="jd-view-toggle">
                <button className={layout === "grid" ? "active" : ""} onClick={() => setLayout("grid")} title="Grid">
                  ▦
                </button>
                <button className={layout === "list" ? "active" : ""} onClick={() => setLayout("list")} title="List">
                  ≡
                </button>
              </div>
              <select
                className="jd-select mono"
                style={{ width: "auto" }}
                value={sort}
                onChange={(e) => setSort(e.target.value as Sort)}
              >
                <option value="date">Date Posted</option>
                <option value="company">Company (A→Z)</option>
              </select>
            </div>

            {activePills.length > 0 && (
              <div className="jd-active-filters">
                {activePills.map((p) => (
                  <button key={p.id + p.label} className="jd-filter-pill" onClick={p.remove}>
                    × {p.label}
                  </button>
                ))}
                <button
                  className="jd-filter-clear"
                  onClick={() => {
                    setForm({ ...INITIAL, keywords: [] });
                    setFilters(EMPTY_FILTERS);
                  }}
                >
                  Clear all
                </button>
              </div>
            )}

            {status === "loading" && <SkeletonGrid layout={layout} />}
            {status === "error" && <ErrorState message={error} onRetry={runSearch} />}
            {status === "success" && groupedVisible.length === 0 && (
              <EmptyState onAdjust={() => setView("search")} />
            )}
            {status === "success" && groupedVisible.length > 0 && (
              <div className="jd-grouped-results">
                {groupedVisible.map((cg) => {
                  const flag = COUNTRY_FLAGS[cg.country.toLowerCase()] || "🌐";
                  const totalJobsInCountry = cg.job_boards.reduce((acc, jb) => acc + jb.jobs.length, 0);
                  return (
                    <section key={cg.country} className="jd-country-section">
                      <div className="jd-country-header">
                        <h2>
                          <span className="flag">{flag}</span> {cg.country}
                        </h2>
                        <span className="badge">{totalJobsInCountry} jobs</span>
                      </div>

                      <div className="jd-job-boards">
                        {cg.job_boards.map((jb) => {
                          const siteClass = jb.name.toLowerCase();
                          const platformLabel = SITE_LABEL[siteClass] ?? jb.name;
                          return (
                            <div key={jb.name} className="jd-board-section">
                              <div className="jd-board-header">
                                <span className={`jd-platform-title ${siteClass}`}>
                                  {siteClass === "linkedin" && (
                                    <img
                                      src={linkedinIcon}
                                      className="jd-platform-icon"
                                      alt=""
                                      style={{ width: "14px", height: "14px", marginRight: "6px" }}
                                    />
                                  )}
                                  {siteClass === "indeed" && (
                                    <img
                                      src={indeedIcon}
                                      className="jd-platform-icon"
                                      alt=""
                                      style={{ width: "14px", height: "14px", marginRight: "6px" }}
                                    />
                                  )}
                                  {platformLabel}
                                </span>
                                <span className="board-badge">{jb.jobs.length} roles</span>
                              </div>
                              <div className={`jd-cards ${layout}`}>
                                {jb.jobs.map((j, i) => (
                                  <JobCard key={`${j.site}-${j.id}-${i}`} job={j} index={i} layout={layout} />
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </section>
                  );
                })}
              </div>
            )}

            {status === "success" && (groupedVisible.length > 0 || form.offset > 0) && (
              <div className="jd-pagination">
                <button
                  type="button"
                  className="jd-btn"
                  disabled={form.offset === 0 || status === "loading"}
                  onClick={() => handlePageChange(form.offset - form.limit)}
                >
                  ← Previous Page
                </button>
                <span className="jd-page-info">
                  Page <b>{Math.floor(form.offset / form.limit) + 1}</b> of <b>{Math.max(1, Math.ceil(totalJobs / form.limit))}</b>
                </span>
                <button
                  type="button"
                  className="jd-btn"
                  disabled={form.offset + form.limit >= totalJobs || status === "loading"}
                  onClick={() => handlePageChange(form.offset + form.limit)}
                >
                  Next Page →
                </button>
              </div>
            )}
          </main>

          <button className="jd-fab" onClick={() => setDrawerOpen(true)}>
            Filters
          </button>
          {drawerOpen && (
            <>
              <div className="jd-drawer-bd" onClick={() => setDrawerOpen(false)} />
              <div className="jd-drawer">
                <button className="jd-btn close" onClick={() => setDrawerOpen(false)}>
                  Close
                </button>
                <h3 style={{ margin: "4px 0 16px", fontFamily: "Sora" }}>Filters</h3>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <FilterSidebar results={allJobs} filters={filters} onChange={patchFilters} />
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
