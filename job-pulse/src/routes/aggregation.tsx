import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { TopNav } from "@/features/jobs/components/TopNav";
import { postAggregate, getCacheStats, deleteCache } from "@/features/jobs/api";
import type { CacheStatsResponse } from "@/features/jobs/types";
import "@/features/jobs/jobdork.css";

interface AggregationHistoryItem {
  id: string;
  time: string;
  status: "success" | "error" | "loading";
  message: string;
}

export const Route = createFileRoute("/aggregation")({
  head: () => ({
    meta: [
      { title: "Aggregation Dashboard — Engine Control" },
      { name: "description", content: "Trigger full scraping and manage deduplication cache." },
    ],
  }),
  component: AggregationPage,
});

function AggregationPage() {
  const [stats, setStats] = useState<CacheStatsResponse | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [clearingCache, setClearingCache] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Aggregation history log
  const [history, setHistory] = useState<AggregationHistoryItem[]>([]);

  const fetchStats = async () => {
    setLoadingStats(true);
    try {
      const data = await getCacheStats();
      setStats(data);
      setError(null);
    } catch (err: unknown) {
      setError("Failed to fetch cache stats. Ensure backend is running.");
      console.error(err);
    } finally {
      setLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const handleTriggerFullAggregation = async () => {
    if (triggering) return;

    setTriggering(true);
    const historyId = Math.random().toString(36).substring(2, 9);
    const newHistoryItem: AggregationHistoryItem = {
      id: historyId,
      time: new Date().toLocaleTimeString(),
      status: "loading",
      message: "Initiating global aggregation...",
    };

    setHistory((prev) => [newHistoryItem, ...prev]);

    try {
      const response = await postAggregate();
      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId
            ? { ...item, status: "success", message: response.message || "Full aggregation task scheduled." }
            : item
        )
      );
      // Wait a moment and refresh stats, though aggregation runs in background
      setTimeout(fetchStats, 1000);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to trigger aggregation";
      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId ? { ...item, status: "error", message: errMsg } : item
        )
      );
    } finally {
      setTriggering(false);
    }
  };

  const handleClearCache = async () => {
    if (clearingCache || !confirm("Are you sure you want to clear the deduplication cache? This will reset all tracked URLs.")) return;

    setClearingCache(true);
    try {
      const response = await deleteCache();
      alert(response.message || "Cache cleared successfully.");
      await fetchStats();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to clear cache");
    } finally {
      setClearingCache(false);
    }
  };

  // Format Date ISO strings nicely
  const formatDate = (isoString: string | null) => {
    if (!isoString) return "No entries";
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <div className="jobdork">
      <TopNav />

      <div className="jd-aggregation-page">
        <div className="jd-page-header">
          <h1>Global Aggregation Dashboard</h1>
          <p>
            Trigger the full job search aggregation pipeline and manage the system deduplication cache.
          </p>
        </div>

        {error && (
          <div className="jd-card" style={{ marginBottom: "24px", border: "1px solid var(--jd-red)" }}>
            <p style={{ color: "var(--jd-red)", margin: 0 }}>{error}</p>
          </div>
        )}

        {/* Dashboard Stats Panel */}
        <div className="jd-dashboard-grid">
          <div className="jd-stat-card">
            <span className="label">Cache Size</span>
            <span className="value gradient">
              {loadingStats ? "..." : stats?.seen_urls ?? 0}
            </span>
            <span className="desc">Total job URLs tracked for deduplication</span>
          </div>

          <div className="jd-stat-card">
            <span className="label">Cache Status</span>
            <span className="value" style={{ fontSize: "20px", height: "34px", display: "flex", alignItems: "center" }}>
              {loadingStats ? "Loading..." : (stats?.seen_urls ?? 0) > 0 ? "Active Cache" : "Empty Cache"}
            </span>
            <span className="desc">Current state of deduplication cache</span>
          </div>

          <div className="jd-stat-card">
            <span className="label">Oldest Cached Job</span>
            <span className="value" style={{ fontSize: "14px", height: "34px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "flex", alignItems: "center" }}>
              {loadingStats ? "..." : formatDate(stats?.oldest_entry ?? null)}
            </span>
            <span className="desc">Timestamp of the oldest cache entry</span>
          </div>
        </div>

        <div className="jd-grid-2">
          {/* Action Card */}
          <div className="jd-card">
            <h3 style={{ margin: "0 0 16px", fontFamily: "Sora", fontWeight: 600 }}>Engine Actions</h3>
            <p style={{ color: "var(--jd-muted)", fontSize: "14px", marginBottom: "24px", lineHeight: "1.5" }}>
              Running a full aggregation triggers all registered scrapers and Google Search templates in parallel in the backend. 
              The backend will parse new jobs, save them directly to the database, and cache their fingerprints to prevent duplicates for 1 hour.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <button
                className="jd-btn primary"
                style={{ width: "100%", justifyContent: "center", padding: "14px" }}
                onClick={handleTriggerFullAggregation}
                disabled={triggering}
              >
                {triggering ? "Running Full Aggregation..." : "Trigger Full Aggregation"}
              </button>

              <button
                className="jd-btn"
                style={{ width: "100%", justifyContent: "center", padding: "10px", borderColor: "rgba(239, 68, 68, 0.2)" }}
                onClick={handleClearCache}
                disabled={clearingCache}
              >
                {clearingCache ? "Clearing Cache..." : "Clear Deduplication Cache"}
              </button>

              <button
                className="jd-btn ghost"
                style={{ width: "100%", justifyContent: "center" }}
                onClick={fetchStats}
                disabled={loadingStats}
              >
                Refresh Stats
              </button>
            </div>
          </div>

          {/* Activity Logs */}
          <div className="jd-history-panel" style={{ marginTop: 0 }}>
            <div className="jd-history-title">
              <span>🔄</span> Aggregation Activity Logs
            </div>
            {history.length === 0 ? (
              <p className="mono" style={{ color: "var(--jd-muted-2)", textAlign: "center", margin: "40px 0" }}>
                No global aggregation triggers executed in this session.
              </p>
            ) : (
              <div className="jd-history-list" style={{ maxHeight: "260px" }}>
                {history.map((item) => (
                  <div key={item.id} className={`jd-history-item ${item.status}`}>
                    <div>
                      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                        <span className="time">[{item.time}]</span>
                        <span style={{ fontWeight: 600 }}>Global Aggregation</span>
                      </div>
                      <div style={{ color: "var(--jd-muted-2)", marginTop: "4px", fontSize: "11px" }}>
                        {item.message}
                      </div>
                    </div>
                    <div>
                      {item.status === "loading" && (
                        <span style={{ color: "var(--jd-amber)" }}>● Triggering</span>
                      )}
                      {item.status === "success" && (
                        <span style={{ color: "var(--jd-green)" }}>✓ Initiated</span>
                      )}
                      {item.status === "error" && (
                        <span style={{ color: "var(--jd-red)" }}>✗ Failed</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Engine Pipeline Architecture Info */}
        <div className="jd-card" style={{ marginTop: "32px", border: "1px solid var(--jd-border)" }}>
          <h3 style={{ margin: "0 0 16px", fontFamily: "Sora", fontWeight: 600 }}>Engine Architecture Overview</h3>
          <div className="jd-grid-2 three-cols" style={{ gap: "24px" }}>
            <div>
              <h4 style={{ color: "var(--jd-cyan)", fontFamily: "Sora", fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>1. Orchestrator</h4>
              <p style={{ color: "var(--jd-muted)", fontSize: "12px", lineHeight: "1.6" }}>
                The backend orchestrator manages concurrency for regional crawlers. When triggered, it queries local Scrapy & Playwright spiders simultaneously.
              </p>
            </div>
            <div>
              <h4 style={{ color: "var(--jd-cyan)", fontFamily: "Sora", fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>2. Google Dorking</h4>
              <p style={{ color: "var(--jd-muted)", fontSize: "12px", lineHeight: "1.6" }}>
                Runs custom Google Search queries using search templates targetting remote, onsite, and board-specific listings.
              </p>
            </div>
            <div>
              <h4 style={{ color: "var(--jd-cyan)", fontFamily: "Sora", fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>3. Fingerprinting & Deduplication</h4>
              <p style={{ color: "var(--jd-muted)", fontSize: "12px", lineHeight: "1.6" }}>
                Every scraped job has an MD5 fingerprint computed from its URL. Fingerprints are checked against the Redis/memory cache with 1-hour TTL before being written to PostgreSQL.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
