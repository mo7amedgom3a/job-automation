import { useState } from "react";
import type { JobResult } from "../types";
import { formatSalary, isEmpty, jobTypeLabel, monogram, monogramColor, relativeTime, renderLite, SITE_LABEL } from "../utils";
import linkedinIcon from "@/asset/linkedin.svg";
import indeedIcon from "@/asset/indeed.svg";

interface Props { job: JobResult; index: number; layout: "grid" | "list"; }

export function JobCard({ job, index, layout }: Props) {
  const [expanded, setExpanded] = useState(false);
  const salary = formatSalary(job.min_amount, job.max_amount, job.currency, job.interval);
  const rel = relativeTime(job.date_posted);
  const apply = !isEmpty(job.job_url_direct) ? job.job_url_direct : job.job_url;
  const siteClass = (job.site || "").toLowerCase();
  const platformLabel = SITE_LABEL[siteClass] ?? job.site;

  return (
    <article className="jd-jc" style={{ animationDelay: `${Math.min(index, 20) * 30}ms` }}>
      <div className="jd-jc-top">
        <div className="jd-jc-logo" style={{ background: job.company_logo ? "transparent" : monogramColor(job.company || "?") }}>
          {job.company_logo ? <img src={job.company_logo} alt="" loading="lazy" /> : monogram(job.company || "?")}
        </div>
        <div className="jd-jc-head">
          <h3 className="jd-jc-title">{job.title || "Untitled role"}</h3>
          <div className="jd-jc-sub">
            {!isEmpty(job.company) && <span>{job.company}</span>}
            {!isEmpty(job.location) && <span className="jd-jc-loc">{job.location}</span>}
          </div>
        </div>
        <span className={`jd-platform ${siteClass}`} style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
          {siteClass === "linkedin" && <img src={linkedinIcon} className="jd-platform-icon" alt="" style={{ width: "12px", height: "12px" }} />}
          {siteClass === "indeed" && <img src={indeedIcon} className="jd-platform-icon" alt="" style={{ width: "12px", height: "12px" }} />}
          {siteClass === "google" && (
            <svg viewBox="0 0 24 24" className="jd-platform-icon" style={{ width: "12px", height: "12px" }}>
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22c-.87-2.6-3.3-4.53-6.16-4.53z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
            </svg>
          )}
          <span>{platformLabel}</span>
        </span>
      </div>

      <div className="jd-jc-tags">
        {job.is_remote && <span className="jd-mini cyan">Remote</span>}
        {!isEmpty(job.job_type) && <span className="jd-mini amber">{jobTypeLabel(job.job_type)}</span>}
        {job.easy_apply && <span className="jd-mini green">⚡ Easy Apply</span>}
        {!isEmpty(job.job_level) && <span className="jd-mini muted">{job.job_level}</span>}
        {rel && <span className="jd-mini muted mono">{rel}</span>}
      </div>

      {salary && <div className="jd-salary">{salary}</div>}

      {layout === "list" && !isEmpty(job.description) && (
        <div className="jd-desc">
          {expanded ? (
            <div dangerouslySetInnerHTML={renderLite(job.description)} />
          ) : (
            <span>{job.description.slice(0, 120)}{job.description.length > 120 ? "…" : ""}</span>
          )}
          {job.description.length > 120 && (
            <div>
              <button className="jd-readmore" onClick={() => setExpanded((v) => !v)}>
                {expanded ? "Show less" : "Read more"}
              </button>
            </div>
          )}
        </div>
      )}

      <div className="jd-jc-foot">
        <div className="meta">
          {[job.company_num_employees, job.company_industry].filter((x) => !isEmpty(x)).join(" · ")}
        </div>
        <div className="actions">
          {!isEmpty(job.job_url) && (
            <a className="jd-btn" href={job.job_url} target="_blank" rel="noreferrer">View Post</a>
          )}
          {!isEmpty(apply) && (
            <a className="jd-btn primary" href={apply} target="_blank" rel="noreferrer">Apply ↗</a>
          )}
        </div>
      </div>
    </article>
  );
}
