import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { TopNav } from "@/features/jobs/components/TopNav";
import { deleteOldJobs, type DeleteOldJobsParams } from "@/features/jobs/api";
import type { Job } from "@/features/jobs/types";
import "@/features/jobs/jobdork.css";

interface CleanupHistoryItem {
  id: string;
  time: string;
  type: "relative" | "range" | "truncate";
  details: string;
  status: "success" | "error" | "loading";
  deletedCount: number;
  message: string;
}

export const Route = createFileRoute("/cleanup")({
  head: () => ({
    meta: [
      { title: "Database Cleanup — JobDork" },
      { name: "description", content: "Delete old job postings or wipe the database." },
    ],
  }),
  component: CleanupPage,
});

function CleanupPage() {
  const [activeTab, setActiveTab] = useState<"relative" | "range" | "truncate">("relative");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<{
    count: number;
    jobs: Job[];
  } | null>(null);

  // Form parameters
  const [days, setDays] = useState<number>(2);
  const [hours, setHours] = useState<number>(0);
  const [minutes, setMinutes] = useState<number>(0);
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [confirmTruncateText, setConfirmTruncateText] = useState<string>("");

  // History log
  const [history, setHistory] = useState<CleanupHistoryItem[]>([]);

  const handleCleanupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setSuccessResult(null);

    const params: DeleteOldJobsParams = {};
    let detailsStr = "";
    let historyId = Math.random().toString(36).substring(2, 9);

    if (activeTab === "relative") {
      params.days = days;
      params.hours = hours;
      params.minutes = minutes;
      params.truncate = false;
      detailsStr = `Older than ${days}d ${hours}h ${minutes}m`;
    } else if (activeTab === "range") {
      if (!startDate && !endDate) {
        setError("Please specify at least a start date or an end date.");
        return;
      }
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) params.end_date = new Date(endDate).toISOString();
      params.truncate = false;
      detailsStr = `Range: ${startDate || "Any"} to ${endDate || "Any"}`;
    } else if (activeTab === "truncate") {
      if (confirmTruncateText !== "DELETE ALL") {
        setError("Please type 'DELETE ALL' exactly to confirm database wipe.");
        return;
      }
      params.truncate = true;
      detailsStr = "Database Truncation (Full Wipe)";
    }

    setLoading(true);

    const newHistoryItem: CleanupHistoryItem = {
      id: historyId,
      time: new Date().toLocaleTimeString(),
      type: activeTab,
      details: detailsStr,
      status: "loading",
      deletedCount: 0,
      message: "Processing deletion request...",
    };

    setHistory((prev) => [newHistoryItem, ...prev]);

    try {
      const response = await deleteOldJobs(params);
      setSuccessResult({
        count: response.deleted_count,
        jobs: response.deleted_jobs,
      });

      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId
            ? {
                ...item,
                status: "success",
                deletedCount: response.deleted_count,
                message: `Successfully deleted ${response.deleted_count} jobs.`,
              }
            : item
        )
      );

      if (activeTab === "truncate") {
        setConfirmTruncateText("");
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to execute deletion";
      setError(errMsg);
      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId ? { ...item, status: "error", message: errMsg } : item
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="jobdork">
      <TopNav />

      <div className="jd-control-page">
        <div className="jd-page-header">
          <h1>Database Cleanup Panel</h1>
          <p>
            Remove outdated job listings or perform database maintenance to keep the aggregation engine fast.
          </p>
        </div>

        <div className="jd-grid-2">
          <div>
            {/* Mode selection tabs */}
            <div
              className="jd-country-tabs"
              style={{
                background: "rgba(255, 255, 255, 0.02)",
                padding: "4px",
                borderRadius: "8px",
                marginBottom: "20px",
                border: "1px solid var(--jd-border)",
                display: "flex",
                gap: "4px",
              }}
            >
              <button
                type="button"
                className={`jd-country-tab ${activeTab === "relative" ? "active" : ""}`}
                style={{ flex: 1, padding: "8px", justifyContent: "center" }}
                onClick={() => {
                  setActiveTab("relative");
                  setError(null);
                  setSuccessResult(null);
                }}
              >
                Relative Age
              </button>
              <button
                type="button"
                className={`jd-country-tab ${activeTab === "range" ? "active" : ""}`}
                style={{ flex: 1, padding: "8px", justifyContent: "center" }}
                onClick={() => {
                  setActiveTab("range");
                  setError(null);
                  setSuccessResult(null);
                }}
              >
                Date Range
              </button>
              <button
                type="button"
                className={`jd-country-tab ${activeTab === "truncate" ? "active" : ""}`}
                style={{
                  flex: 1,
                  padding: "8px",
                  justifyContent: "center",
                  color: activeTab === "truncate" ? "var(--jd-text)" : "rgba(239, 68, 68, 0.7)",
                }}
                onClick={() => {
                  setActiveTab("truncate");
                  setError(null);
                  setSuccessResult(null);
                }}
              >
                ⚠️ Danger Zone
              </button>
            </div>

            <div className="jd-card">
              <form onSubmit={handleCleanupSubmit}>
                {activeTab === "relative" && (
                  <>
                    <h3 style={{ margin: "0 0 16px", fontFamily: "Sora", fontWeight: 600 }}>Relative Age Cleanup</h3>
                    <p style={{ color: "var(--jd-muted)", fontSize: "13px", marginBottom: "20px", lineHeight: "1.5" }}>
                      Deletes jobs that were scraped older than the specified days, hours, and minutes ago. If all values are set to 0, it defaults to deleting jobs older than 2 days.
                    </p>

                    <div className="jd-form-group">
                      <label htmlFor="days-input">Days</label>
                      <input
                        type="number"
                        id="days-input"
                        className="jd-input mono"
                        min="0"
                        value={days}
                        onChange={(e) => setDays(Math.max(0, parseInt(e.target.value) || 0))}
                      />
                    </div>

                    <div className="jd-form-group">
                      <label htmlFor="hours-input">Hours</label>
                      <input
                        type="number"
                        id="hours-input"
                        className="jd-input mono"
                        min="0"
                        max="23"
                        value={hours}
                        onChange={(e) => setHours(Math.max(0, Math.min(23, parseInt(e.target.value) || 0)))}
                      />
                    </div>

                    <div className="jd-form-group">
                      <label htmlFor="minutes-input">Minutes</label>
                      <input
                        type="number"
                        id="minutes-input"
                        className="jd-input mono"
                        min="0"
                        max="59"
                        value={minutes}
                        onChange={(e) => setMinutes(Math.max(0, Math.min(59, parseInt(e.target.value) || 0)))}
                      />
                    </div>
                  </>
                )}

                {activeTab === "range" && (
                  <>
                    <h3 style={{ margin: "0 0 16px", fontFamily: "Sora", fontWeight: 600 }}>Date Range Cleanup</h3>
                    <p style={{ color: "var(--jd-muted)", fontSize: "13px", marginBottom: "20px", lineHeight: "1.5" }}>
                      Deletes jobs scraped within a specific timeframe. You can specify a start date, end date, or both.
                    </p>

                    <div className="jd-form-group">
                      <label htmlFor="start-date">Start Date & Time (Inclusive)</label>
                      <input
                        type="datetime-local"
                        id="start-date"
                        className="jd-input mono"
                        style={{ colorScheme: "dark" }}
                        value={startDate}
                        onChange={(e) => setStartDate(e.target.value)}
                      />
                    </div>

                    <div className="jd-form-group">
                      <label htmlFor="end-date">End Date & Time (Inclusive)</label>
                      <input
                        type="datetime-local"
                        id="end-date"
                        className="jd-input mono"
                        style={{ colorScheme: "dark" }}
                        value={endDate}
                        onChange={(e) => setEndDate(e.target.value)}
                      />
                    </div>
                  </>
                )}

                {activeTab === "truncate" && (
                  <>
                    <h3 style={{ margin: "0 0 16px", fontFamily: "Sora", fontWeight: 600, color: "var(--jd-red)" }}>
                      Wipe Database (Truncate)
                    </h3>
                    <p style={{ color: "var(--jd-muted)", fontSize: "13px", marginBottom: "20px", lineHeight: "1.5" }}>
                      This operation is destructive and cannot be undone. It will remove **ALL** job postings currently stored in the PostgreSQL database.
                    </p>

                    <div
                      className="jd-form-group"
                      style={{
                        padding: "12px",
                        background: "rgba(239, 68, 68, 0.05)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        borderRadius: "8px",
                        marginBottom: "20px",
                      }}
                    >
                      <label htmlFor="confirm-trunc" style={{ color: "var(--jd-red)" }}>
                        Confirm Deletion
                      </label>
                      <p style={{ color: "var(--jd-muted)", fontSize: "12px", margin: "4px 0 12px" }}>
                        Type <b style={{ color: "var(--jd-text)" }}>DELETE ALL</b> below to authorize this action:
                      </p>
                      <input
                        type="text"
                        id="confirm-trunc"
                        className="jd-input mono"
                        placeholder="Type DELETE ALL"
                        value={confirmTruncateText}
                        onChange={(e) => setConfirmTruncateText(e.target.value)}
                      />
                    </div>
                  </>
                )}

                {error && (
                  <div
                    style={{
                      padding: "12px",
                      background: "rgba(239, 68, 68, 0.1)",
                      border: "1px solid var(--jd-red)",
                      borderRadius: "6px",
                      color: "var(--jd-text)",
                      fontSize: "13px",
                      marginBottom: "16px",
                    }}
                  >
                    ❌ {error}
                  </div>
                )}

                <button
                  type="submit"
                  className={`jd-btn ${activeTab === "truncate" ? "destructive" : "primary"}`}
                  style={{
                    width: "100%",
                    justifyContent: "center",
                    padding: "12px",
                    background: activeTab === "truncate" ? "var(--jd-red)" : undefined,
                  }}
                  disabled={loading}
                >
                  {loading ? "Deleting Jobs..." : activeTab === "truncate" ? "Wipe All Database Jobs" : "Delete Selected Jobs"}
                </button>
              </form>
            </div>
          </div>

          <div>
            {/* History Panel */}
            <div className="jd-history-panel" style={{ marginTop: 0 }}>
              <div className="jd-history-title">
                <span>🗑️</span> Deletion Activity Logs
              </div>
              {history.length === 0 ? (
                <p className="mono" style={{ color: "var(--jd-muted-2)", textAlign: "center", margin: "40px 0" }}>
                  No deletion operations performed in this session.
                </p>
              ) : (
                <div className="jd-history-list" style={{ maxHeight: "400px" }}>
                  {history.map((item) => (
                    <div key={item.id} className={`jd-history-item ${item.status === "error" ? "error" : "success"}`}>
                      <div>
                        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                          <span className="time">[{item.time}]</span>
                          <span style={{ fontWeight: 600, textTransform: "capitalize" }}>{item.type}</span>
                          <span style={{ color: "var(--jd-muted-2)" }}>({item.details})</span>
                        </div>
                        <div style={{ color: "var(--jd-muted)", marginTop: "4px", fontSize: "11px" }}>
                          {item.message}
                        </div>
                      </div>
                      <div>
                        {item.status === "loading" && (
                          <span style={{ color: "var(--jd-amber)" }}>● Running</span>
                        )}
                        {item.status === "success" && (
                          <span style={{ color: "var(--jd-green)" }}>
                            ✓ Deleted {item.deletedCount}
                          </span>
                        )}
                        {item.status === "error" && <span style={{ color: "var(--jd-red)" }}>✗ Error</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Success Result Area */}
        {successResult && (
          <div className="jd-card" style={{ marginTop: "32px", border: "1px solid var(--jd-border)" }}>
            <h3 style={{ margin: "0 0 12px", fontFamily: "Sora", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ color: "var(--jd-green)" }}>✓</span> Cleanup Completed
            </h3>
            <p style={{ color: "var(--jd-muted)", fontSize: "14px", marginBottom: "20px" }}>
              Successfully removed <b>{successResult.count}</b> job listings from the database.
            </p>

            {successResult.jobs.length > 0 ? (
              <div style={{ overflowX: "auto" }}>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    fontSize: "12px",
                    fontFamily: "Sora, sans-serif",
                    textAlign: "left",
                  }}
                >
                  <thead>
                    <tr style={{ borderBottom: "1px solid rgba(255, 106, 0, 0.2)", color: "var(--jd-muted)" }}>
                      <th style={{ padding: "8px" }}>Job Title</th>
                      <th style={{ padding: "8px" }}>Company</th>
                      <th style={{ padding: "8px" }}>Location</th>
                      <th style={{ padding: "8px" }}>Source</th>
                      <th style={{ padding: "8px" }}>Scraped At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {successResult.jobs.map((job, idx) => (
                      <tr
                        key={job.id + idx}
                        style={{
                          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                          background: idx % 2 === 0 ? "rgba(255, 255, 255, 0.01)" : "transparent",
                        }}
                      >
                        <td style={{ padding: "10px 8px", fontWeight: 600, color: "var(--jd-text)" }}>
                          {job.title}
                        </td>
                        <td style={{ padding: "10px 8px", color: "var(--jd-muted)" }}>{job.company}</td>
                        <td style={{ padding: "10px 8px", color: "var(--jd-muted)" }}>{job.location}</td>
                        <td style={{ padding: "10px 8px" }}>
                          <span className="spider-badge">{job.source || job.site}</span>
                        </td>
                        <td className="mono" style={{ padding: "10px 8px", color: "var(--jd-muted-2)" }}>
                          {new Date(job.scraped_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mono" style={{ color: "var(--jd-muted-2)", fontStyle: "italic", margin: "10px 0 0" }}>
                No listing details returned.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
