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
