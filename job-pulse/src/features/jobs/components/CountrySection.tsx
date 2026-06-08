import { useState, useMemo } from "react";
import type { CountryGroup, Job } from "../types";
import { JobCard } from "./JobCard";
import { SITE_LABEL } from "../utils";
import linkedinIcon from "@/asset/linkedin.svg";
import indeedIcon from "@/asset/indeed.svg";

interface Props {
  cg: CountryGroup;
  layout: "grid" | "list";
  sort: "date" | "company";
  flag: string;
}

export function CountrySection({ cg, layout, sort, flag }: Props) {
  const [activeSource, setActiveSource] = useState<string>("all");

  // Get all unique sources (job boards) available in this country group with their counts
  const sources = useMemo(() => {
    return cg.job_boards
      .map((jb) => ({
        name: jb.name,
        id: jb.name.toLowerCase(),
        count: jb.jobs.length,
      }))
      .filter((s) => s.count > 0);
  }, [cg.job_boards]);

  const totalJobsInCountry = useMemo(() => {
    return cg.job_boards.reduce((acc, jb) => acc + jb.jobs.length, 0);
  }, [cg.job_boards]);

  // Combine, filter, and sort active jobs in this country
  const filteredSortedJobs = useMemo(() => {
    const list: Job[] = [];
    cg.job_boards.forEach((jb) => {
      const siteId = jb.name.toLowerCase();
      if (activeSource === "all" || activeSource === siteId) {
        jb.jobs.forEach((j) => {
          list.push({
            ...j,
            site: jb.name, // Ensure job site is set correctly
          });
        });
      }
    });

    if (sort === "date") {
      list.sort((a, b) => {
        const da = a.scraped_at ? new Date(a.scraped_at).getTime() : 0;
        const db = b.scraped_at ? new Date(b.scraped_at).getTime() : 0;
        return db - da;
      });
    } else if (sort === "company") {
      list.sort((a, b) => (a.company || "").localeCompare(b.company || ""));
    }

    return list;
  }, [cg.job_boards, activeSource, sort]);

  // If there are no jobs in this country section, don't show it at all
  if (totalJobsInCountry === 0) return null;

  const showTabs = sources.length > 1;

  return (
    <section className="jd-country-section">
      <div className="jd-country-header">
        <h2>
          <span className="flag">{flag}</span> {cg.country}
        </h2>
        <span className="badge">{totalJobsInCountry} jobs</span>
      </div>

      <div className="jd-job-boards">
        {showTabs && (
          <div className="jd-source-tabs">
            <button
              type="button"
              className={`jd-source-tab-btn ${activeSource === "all" ? "active" : ""}`}
              onClick={() => setActiveSource("all")}
            >
              <svg
                viewBox="0 0 24 24"
                className="jd-tab-icon"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{ width: "14px", height: "14px" }}
                aria-hidden="true"
              >
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
              <span>All Sources</span>
              <span className="jd-tab-badge">{totalJobsInCountry}</span>
            </button>
            {sources.map((src) => {
              const platformLabel = SITE_LABEL[src.id] ?? src.name;
              return (
                <button
                  key={src.id}
                  type="button"
                  className={`jd-source-tab-btn ${activeSource === src.id ? "active" : ""}`}
                  onClick={() => setActiveSource(src.id)}
                >
                  {src.id === "linkedin" && (
                    <img src={linkedinIcon} className="jd-tab-icon" alt="" />
                  )}
                  {src.id === "indeed" && (
                    <img src={indeedIcon} className="jd-tab-icon" alt="" />
                  )}
                  {src.id === "google" && (
                    <svg
                      viewBox="0 0 24 24"
                      className="jd-tab-icon"
                      style={{ width: "14px", height: "14px" }}
                      aria-hidden="true"
                    >
                      <path
                        fill="#4285F4"
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22c-.87-2.6-3.3-4.53-6.16-4.53z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                      />
                    </svg>
                  )}
                  {src.id !== "linkedin" && src.id !== "indeed" && src.id !== "google" && (
                    <svg
                      viewBox="0 0 24 24"
                      className="jd-tab-icon"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      style={{ width: "14px", height: "14px" }}
                      aria-hidden="true"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
                    </svg>
                  )}
                  <span>{platformLabel}</span>
                  <span className="jd-tab-badge">{src.count}</span>
                </button>
              );
            })}
          </div>
        )}

        <div className={`jd-cards ${layout}`}>
          {filteredSortedJobs.map((job, idx) => (
            <JobCard key={`${job.site}-${job.id}-${idx}`} job={job} index={idx} layout={layout} />
          ))}
        </div>
      </div>
    </section>
  );
}
