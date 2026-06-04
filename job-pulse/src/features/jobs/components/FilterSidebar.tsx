import { useMemo } from "react";
import type { Job } from "../types";
import { isEmpty } from "../utils";

export interface ClientFilters {
  companies: string[];
  locations: string[];
  remoteOnly: boolean;
  tags: string[];
}

interface Props {
  results: Job[];
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
  const tags = useMemo(() => {
    const allTags = results.flatMap((r) => r.tags || []);
    return counts(allTags.filter((x) => !isEmpty(x))).slice(0, 10);
  }, [results]);

  const toggle = <K extends "companies" | "locations" | "tags">(key: K, v: string) => {
    const cur = filters[key];
    const next = cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v];
    onChange({ [key]: next } as unknown as Partial<ClientFilters>);
  };

  return (
    <>
      <div className="jd-panel">
        <h4>Remote</h4>
        <label className="jd-switch">
          <input
            type="checkbox"
            checked={filters.remoteOnly}
            onChange={(e) => onChange({ remoteOnly: e.target.checked })}
          />
          <span className="track" />
          <span>Remote only</span>
        </label>
      </div>

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

      {tags.length > 0 && (
        <div className="jd-panel">
          <h4>Tags / Tech</h4>
          <div className="jd-checklist">
            {tags.map((t) => (
              <label key={t.v}>
                <input type="checkbox" checked={filters.tags.includes(t.v)} onChange={() => toggle("tags", t.v)} />
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{t.v}</span>
                <span className="count">{t.n}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
