import { useState } from "react";
import type { FormState } from "../types";

const COUNTRIES = ["USA", "Egypt", "Saudi Arabia", "UAE", "Qatar", "Kuwait", "Bahrain", "Oman", "UK", "Germany", "Canada"];

interface Props {
  value: FormState;
  onChange: (patch: Partial<FormState>) => void;
  onSubmit: () => void;
  loading: boolean;
}

export function SearchForm({ value, onChange, onSubmit, loading }: Props) {
  const [countryOpen, setCountryOpen] = useState(false);
  const [countryQuery, setCountryQuery] = useState("");
  const [tagDraft, setTagDraft] = useState("");

  const addTag = (raw: string) => {
    const t = raw.trim().replace(/,$/, "");
    if (!t) return;
    if (value.keywords.includes(t)) return;
    onChange({ keywords: [...value.keywords, t] });
  };
  const removeTag = (t: string) => onChange({ keywords: value.keywords.filter((x) => x !== t) });

  const toggleCountry = (c: string) => {
    const norm = c.toLowerCase();
    onChange({
      countries: value.countries.includes(norm)
        ? value.countries.filter((x) => x !== norm)
        : [...value.countries, norm],
    });
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
                {t}
                <button type="button" onClick={() => removeTag(t)} aria-label={`remove ${t}`}>
                  ×
                </button>
              </span>
            ))}
            <input
              value={tagDraft}
              onChange={(e) => {
                const v = e.target.value;
                if (v.endsWith(",")) {
                  addTag(v);
                  setTagDraft("");
                } else {
                  setTagDraft(v);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addTag(tagDraft);
                  setTagDraft("");
                }
                if (e.key === "Backspace" && !tagDraft && value.keywords.length) {
                  removeTag(value.keywords[value.keywords.length - 1]);
                }
              }}
              placeholder={value.keywords.length ? "" : 'e.g. "DevOps", "FastAPI", "Go" — press Enter to add'}
            />
          </div>
        </div>
      </div>

      {/* Row 2 - Filters */}
      <div className="jd-row cols-3">
        <div className="jd-combo">
          <label className="jd-label">Countries</label>
          <button
            type="button"
            className="jd-input"
            style={{ textAlign: "left", cursor: "pointer" }}
            onClick={() => setCountryOpen((v) => !v)}
          >
            <span className="mono" style={{ fontSize: 12, color: "var(--jd-muted)" }}>
              {value.countries.length ? `${value.countries.length} selected` : "All Countries (Select…)"}
            </span>
          </button>
          {countryOpen && (
            <div className="jd-combo-pop">
              <div style={{ padding: 8, borderBottom: "1px solid var(--jd-border)" }}>
                <input
                  className="jd-input"
                  placeholder="Search countries…"
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
                <span key={c} className="jd-tag">
                  {c}
                  <button type="button" onClick={() => toggleCountry(c)}>
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="jd-label">Company (optional)</label>
          <input
            className="jd-input"
            placeholder="e.g. Google, Microsoft"
            value={value.company || ""}
            onChange={(e) => onChange({ company: e.target.value || null })}
          />
        </div>

        <div>
          <label className="jd-label">Work Type</label>
          <div className="jd-tabs" style={{ display: "flex", borderBottom: "none", gap: "2px", background: "var(--jd-surface-2)", padding: "4px", borderRadius: "8px" }}>
            <button
              type="button"
              className={value.remote === null ? "active" : ""}
              onClick={() => onChange({ remote: null })}
              style={{ flex: 1, padding: "6px 8px", fontSize: "12px", borderRadius: "6px" }}
            >
              Any
            </button>
            <button
              type="button"
              className={value.remote === true ? "active" : ""}
              onClick={() => onChange({ remote: true })}
              style={{ flex: 1, padding: "6px 8px", fontSize: "12px", borderRadius: "6px" }}
            >
              Remote
            </button>
            <button
              type="button"
              className={value.remote === false ? "active" : ""}
              onClick={() => onChange({ remote: false })}
              style={{ flex: 1, padding: "6px 8px", fontSize: "12px", borderRadius: "6px" }}
            >
              Onsite
            </button>
          </div>
        </div>
      </div>

      {/* Row 3 - Limit & Advanced settings removal */}
      <div className="jd-row">
        <div>
          <label className="jd-label">Max Results</label>
          <div className="jd-slider-row">
            <input
              type="range"
              min={10}
              max={100}
              step={10}
              className="jd-slider"
              value={value.limit}
              onChange={(e) => onChange({ limit: parseInt(e.target.value, 10) })}
            />
            <span className="jd-slider-val">{value.limit}</span>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="button"
        className="jd-cta"
        disabled={loading || value.keywords.length === 0}
        onClick={onSubmit}
        style={{ marginTop: "12px" }}
      >
        {loading ? (
          <>
            <span className="spinner" /> Searching jobs…
          </>
        ) : (
          "Search Jobs"
        )}
      </button>
      {value.keywords.length === 0 && !loading && (
        <p className="mono" style={{ color: "var(--jd-muted)", fontSize: 11, textAlign: "center", marginTop: 10 }}>
          Add at least one keyword to start.
        </p>
      )}
    </div>
  );
}
