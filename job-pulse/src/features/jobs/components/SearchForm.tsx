import { useState } from "react";
import type { FormState, JobTypeOption, PostedWithinKey, SiteId, WorkType } from "../types";
import { SITE_LABEL } from "../utils";

const SITES: SiteId[] = ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"];
const COUNTRIES = ["USA", "Egypt", "Saudi Arabia", "UAE", "Qatar", "Kuwait", "Bahrain", "Oman", "UK", "Germany", "Canada"];
const JOB_TYPES: { v: JobTypeOption; l: string }[] = [
  { v: "any", l: "Any" }, { v: "full-time", l: "Full-Time" },
  { v: "part-time", l: "Part-Time" }, { v: "contract", l: "Contract" },
  { v: "internship", l: "Internship" },
];
const POSTED: { v: PostedWithinKey; l: string }[] = [
  { v: "24h", l: "Last 24 Hours" }, { v: "3d", l: "Last 3 Days" },
  { v: "7d", l: "Last 7 Days" }, { v: "30d", l: "Last 30 Days" },
];

interface Props {
  value: FormState;
  onChange: (patch: Partial<FormState>) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function SearchForm({ value, onChange, onSubmit, loading }: Props) {
  const [tagDraft, setTagDraft] = useState("");
  const [advOpen, setAdvOpen] = useState(false);
  const [countryOpen, setCountryOpen] = useState(false);
  const [countryQuery, setCountryQuery] = useState("");

  const addTag = (raw: string) => {
    const t = raw.trim().replace(/,$/, "");
    if (!t) return;
    if (value.keywords.includes(t)) return;
    onChange({ keywords: [...value.keywords, t] });
  };
  const removeTag = (t: string) => onChange({ keywords: value.keywords.filter((x) => x !== t) });

  const toggleSite = (s: SiteId) => {
    onChange({ jobSites: value.jobSites.includes(s) ? value.jobSites.filter((x) => x !== s) : [...value.jobSites, s] });
  };

  const toggleCountry = (c: string) => {
    const norm = c.toLowerCase();
    onChange({ countries: value.countries.includes(norm) ? value.countries.filter((x) => x !== norm) : [...value.countries, norm] });
  };

  return (
    <div className="jd-card">
      {/* Row 1 — Keywords */}
      <div className="jd-row">
        <div>
          <label className="jd-label">Keywords</label>
          <div className="jd-tags">
            {value.keywords.map((t) => (
              <span key={t} className="jd-tag">
                {t}<button type="button" onClick={() => removeTag(t)} aria-label={`remove ${t}`}>×</button>
              </span>
            ))}
            <input
              value={tagDraft}
              onChange={(e) => {
                const v = e.target.value;
                if (v.endsWith(",")) { addTag(v); setTagDraft(""); }
                else setTagDraft(v);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") { e.preventDefault(); addTag(tagDraft); setTagDraft(""); }
                if (e.key === "Backspace" && !tagDraft && value.keywords.length) removeTag(value.keywords[value.keywords.length - 1]);
              }}
              placeholder={value.keywords.length ? "" : 'e.g. "DevOps", "FastAPI", "Go" — press Enter to add'}
            />
          </div>
        </div>
      </div>

      {/* Row 2 */}
      <div className="jd-row cols-3">
        <div>
          <label className="jd-label">Platforms</label>
          <div className="jd-chips">
            {SITES.map((s) => (
              <button key={s} type="button" className={`jd-chip ${value.jobSites.includes(s) ? "active" : ""}`} onClick={() => toggleSite(s)}>
                {SITE_LABEL[s]}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="jd-label">Work Type</label>
          <div className="jd-tabs">
            {(["remote", "onsite", "both"] as WorkType[]).map((w) => (
              <button key={w} type="button" className={value.workType === w ? "active" : ""} onClick={() => onChange({ workType: w })}>
                {w === "remote" ? "Remote" : w === "onsite" ? "Onsite" : "Both"}
              </button>
            ))}
          </div>
          {value.workType === "onsite" && (
            <input
              className="jd-input"
              style={{ marginTop: 10 }}
              placeholder="City (e.g. Cairo)"
              value={value.onsiteCity}
              onChange={(e) => onChange({ onsiteCity: e.target.value })}
            />
          )}
        </div>

        <div>
          <label className="jd-label">Job Type</label>
          <div className="jd-tabs" style={{ flexWrap: "wrap" }}>
            {JOB_TYPES.map((t) => (
              <button key={t.v} type="button" className={value.jobType === t.v ? "active" : ""} onClick={() => onChange({ jobType: t.v })}>
                {t.l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Row 3 */}
      <div className="jd-row cols-3">
        <div className="jd-combo">
          <label className="jd-label">Countries</label>
          <button type="button" className="jd-input" style={{ textAlign: "left", cursor: "pointer" }} onClick={() => setCountryOpen((v) => !v)}>
            <span className="mono" style={{ fontSize: 12, color: "var(--jd-muted)" }}>
              {value.countries.length ? `${value.countries.length} selected` : "Select countries…"}
            </span>
          </button>
          {countryOpen && (
            <div className="jd-combo-pop">
              <div style={{ padding: 8, borderBottom: "1px solid var(--jd-border)" }}>
                <input
                  className="jd-input"
                  placeholder="Search…"
                  value={countryQuery}
                  onChange={(e) => setCountryQuery(e.target.value)}
                  autoFocus
                />
              </div>
              {COUNTRIES.filter((c) => c.toLowerCase().includes(countryQuery.toLowerCase())).map((c) => {
                const norm = c.toLowerCase();
                const checked = value.countries.includes(norm);
                return (
                  <label key={c}>
                    <input type="checkbox" checked={checked} onChange={() => toggleCountry(c)} />
                    <span>{c}</span>
                  </label>
                );
              })}
            </div>
          )}
          {value.countries.length > 0 && (
            <div className="selected">
              {value.countries.map((c) => (
                <span key={c} className="jd-tag">{c}<button type="button" onClick={() => toggleCountry(c)}>×</button></span>
              ))}
            </div>
          )}
          <label className="jd-switch" style={{ marginTop: "10px", display: "flex", width: "fit-content" }}>
            <input type="checkbox" checked={value.strictCountry} onChange={(e) => onChange({ strictCountry: e.target.checked })} />
            <span className="track" /><span>Strict Country Filtering</span>
          </label>
        </div>

        <div>
          <label className="jd-label">Posted Within</label>
          <select className="jd-select" value={value.postedWithin} onChange={(e) => onChange({ postedWithin: e.target.value as PostedWithinKey })}>
            {POSTED.map((p) => <option key={p.v} value={p.v}>{p.l}</option>)}
          </select>
        </div>

        <div>
          <label className="jd-label">Max Results (per board)</label>
          <div className="jd-slider-row">
            <input
              type="range" min={5} max={100} step={5} className="jd-slider"
              value={value.maxResults} onChange={(e) => onChange({ maxResults: parseInt(e.target.value, 10) })}
            />
            <span className="jd-slider-val">{value.maxResults}</span>
          </div>
        </div>
      </div>

      {/* Row 4 — Advanced */}
      <div style={{ marginBottom: 18 }}>
        <button type="button" className="jd-adv-toggle" onClick={() => setAdvOpen((v) => !v)}>
          ⚙ Advanced Options {advOpen ? "▲" : "▼"}
        </button>
        {advOpen && (
          <div className="jd-adv">
            <label className="jd-switch">
              <input type="checkbox" checked={value.easyApply} onChange={(e) => onChange({ easyApply: e.target.checked })} />
              <span className="track" /><span>Easy Apply Only</span>
            </label>
            <label className="jd-switch">
              <input type="checkbox" checked={value.linkedinFetchDescription} onChange={(e) => onChange({ linkedinFetchDescription: e.target.checked })} />
              <span className="track" /><span>Fetch Full Descriptions (LinkedIn — slower)</span>
            </label>
            <label className="jd-switch">
              <input type="checkbox" checked={value.enforceAnnualSalary} onChange={(e) => onChange({ enforceAnnualSalary: e.target.checked })} />
              <span className="track" /><span>Normalize All Salaries to Annual</span>
            </label>
            {value.workType === "onsite" && (
              <div>
                <label className="jd-label">Distance (miles)</label>
                <div className="jd-slider-row">
                  <input type="range" min={1} max={100} step={1} className="jd-slider"
                    value={value.distance} onChange={(e) => onChange({ distance: parseInt(e.target.value, 10) })} />
                  <span className="jd-slider-val">{value.distance}</span>
                </div>
              </div>
            )}
            <div style={{ gridColumn: "1 / -1" }}>
              <label className="jd-label">Google Jobs Custom Query (optional)</label>
              <input className="jd-input" value={value.googleSearchTerm} onChange={(e) => onChange({ googleSearchTerm: e.target.value })} />
            </div>
          </div>
        )}
      </div>

      {/* Row 5 */}
      <button
        type="button"
        className="jd-cta"
        disabled={loading || value.keywords.length === 0}
        onClick={onSubmit}
      >
        {loading ? (<><span className="spinner" /> Scraping boards…</>) : "Search Jobs"}
      </button>
      {value.keywords.length === 0 && !loading && (
        <p className="mono" style={{ color: "var(--jd-muted)", fontSize: 11, textAlign: "center", marginTop: 10 }}>
          Add at least one keyword to start.
        </p>
      )}
    </div>
  );
}
