import { useMemo } from "react";
import type { JobResult } from "../types";
import { isEmpty } from "../utils";

export interface ClientFilters {
  companies: string[];
  locations: string[];
  remoteOnly: boolean;
  levels: string[];
  functions: string[];
  salary: [number, number] | null;
}

interface Props {
  results: JobResult[];
  filters: ClientFilters;
  onChange: (patch: Partial<ClientFilters>) => void;
}

function counts<T extends string>(items: T[]): Array<{ v: T; n: number }> {
  const m = new Map<T, number>();
  for (const x of items) m.set(x, (m.get(x) ?? 0) + 1);
  return Array.from(m.entries()).map(([v, n]) => ({ v, n })).sort((a, b) => b.n - a.n);
}

export function FilterSidebar({ results, filters, onChange }: Props) {
  const companies = useMemo(() => counts(results.map((r) => r.company).filter((x) => !isEmpty(x))).slice(0, 10), [results]);
  const locations = useMemo(() => counts(results.map((r) => r.location).filter((x) => !isEmpty(x))).slice(0, 10), [results]);
  const levels = useMemo(() => counts(results.map((r) => r.job_level).filter((x) => !isEmpty(x))), [results]);
  const functions = useMemo(() => counts(results.map((r) => r.job_function).filter((x) => !isEmpty(x))), [results]);

  const salaryStats = useMemo(() => {
    const vals: number[] = [];
    results.forEach((r) => {
      const toN = (x: string | number) => {
        if (typeof x === "number") return isNaN(x) ? null : x;
        const t = (x || "").toString().replace(/[,\s]/g, "");
        const n = parseFloat(t);
        return isNaN(n) ? null : n;
      };
      const mn = toN(r.min_amount); const mx = toN(r.max_amount);
      if (mn != null) vals.push(mn);
      if (mx != null) vals.push(mx);
    });
    if (!vals.length) return null;
    return { min: Math.min(...vals), max: Math.max(...vals) };
  }, [results]);

  const toggle = <K extends "companies" | "locations" | "levels" | "functions">(key: K, v: string) => {
    const cur = filters[key];
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
    onChange({ [key]: next } as unknown as Partial<ClientFilters>);
  };

  return (
    <>
      <div className="jd-panel">
        <h4>Remote</h4>
        <label className="jd-switch">
          <input type="checkbox" checked={filters.remoteOnly} onChange={(e) => onChange({ remoteOnly: e.target.checked })} />
          <span className="track" /><span>Remote only</span>
        </label>
      </div>

      {salaryStats && (
        <div className="jd-panel">
          <h4>Salary</h4>
          <div className="mono" style={{ fontSize: 11, color: "var(--jd-muted)", marginBottom: 8 }}>
            {filters.salary ? `${filters.salary[0].toLocaleString()} – ${filters.salary[1].toLocaleString()}` : `${salaryStats.min.toLocaleString()} – ${salaryStats.max.toLocaleString()}`}
          </div>
          <input
            type="range" min={salaryStats.min} max={salaryStats.max}
            value={filters.salary ? filters.salary[0] : salaryStats.min}
            onChange={(e) => onChange({ salary: [parseInt(e.target.value, 10), filters.salary ? filters.salary[1] : salaryStats.max] })}
            className="jd-slider"
          />
          <input
            type="range" min={salaryStats.min} max={salaryStats.max}
            value={filters.salary ? filters.salary[1] : salaryStats.max}
            onChange={(e) => onChange({ salary: [filters.salary ? filters.salary[0] : salaryStats.min, parseInt(e.target.value, 10)] })}
            className="jd-slider" style={{ marginTop: 8 }}
          />
        </div>
      )}

      {companies.length > 0 && (
        <div className="jd-panel">
          <h4>Company</h4>
          <div className="jd-checklist">
            {companies.map((c) => (
              <label key={c.v}>
                <input type="checkbox" checked={filters.companies.includes(c.v)} onChange={() => toggle("companies", c.v)} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.v}</span>
                <span className="count">{c.n}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {locations.length > 0 && (
        <div className="jd-panel">
          <h4>Location</h4>
          <div className="jd-checklist">
            {locations.map((c) => (
              <label key={c.v}>
                <input type="checkbox" checked={filters.locations.includes(c.v)} onChange={() => toggle("locations", c.v)} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.v}</span>
                <span className="count">{c.n}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {levels.length > 0 && (
        <div className="jd-panel">
          <h4>Experience</h4>
          <div className="jd-checklist">
            {levels.map((c) => (
              <label key={c.v}>
                <input type="checkbox" checked={filters.levels.includes(c.v)} onChange={() => toggle("levels", c.v)} />
                <span>{c.v}</span><span className="count">{c.n}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {functions.length > 0 && (
        <div className="jd-panel">
          <h4>Job Function</h4>
          <div className="jd-checklist">
            {functions.map((c) => (
              <label key={c.v}>
                <input type="checkbox" checked={filters.functions.includes(c.v)} onChange={() => toggle("functions", c.v)} />
                <span>{c.v}</span><span className="count">{c.n}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
