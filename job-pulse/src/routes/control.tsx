import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { TopNav } from "@/features/jobs/components/TopNav";
import { getCountries, postSubAggregate } from "@/features/jobs/api";
import type { CountryInfo, CountriesResponse } from "@/features/jobs/types";
import "@/features/jobs/jobdork.css";

const COUNTRY_FLAGS: Record<string, string> = {
  egypt: "🇪🇬",
  usa: "🇺🇸",
  "saudi arabia": "🇸🇦",
  saudi: "🇸🇦",
  uae: "🇦🇪",
  "united arab emirates": "🇦🇪",
  qatar: "🇶🇦",
  kuwait: "🇰🇼",
  bahrain: "🇧🇭",
  oman: "🇴🇲",
  uk: "🇬🇧",
  "united kingdom": "🇬🇧",
  germany: "🇩🇪",
  poland: "🇵🇱",
  spain: "🇪🇸",
  canada: "🇨🇦",
  france: "🇫🇷",
};

interface HistoryItem {
  id: string;
  time: string;
  country: string;
  board: string;
  spider: string;
  status: "success" | "error" | "loading";
  message: string;
}

export const Route = createFileRoute("/control")({
  head: () => ({
    meta: [
      { title: "Control Panel — Scraper Settings" },
      { name: "description", content: "Trigger regional job scrapers manually." },
    ],
  }),
  component: ControlPage,
});

function ControlPage() {
  const [countriesData, setCountriesData] = useState<CountriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [selectedCountryKey, setSelectedCountryKey] = useState<string>("");
  const [selectedBoard, setSelectedBoard] = useState<string>("");
  const [triggering, setTriggering] = useState(false);

  // History state
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const fetchCountries = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCountries();
      setCountriesData(data);
      const keys = Object.keys(data.countries);
      if (keys.length > 0) {
        setSelectedCountryKey(keys[0]);
        const firstCountryInfo = data.countries[keys[0]];
        if (firstCountryInfo.job_boards.length > 0) {
          setSelectedBoard(firstCountryInfo.job_boards[0]);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load countries");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCountries();
  }, []);

  // Sync board selection when country selection changes in manual form
  useEffect(() => {
    if (countriesData && selectedCountryKey) {
      const countryInfo = countriesData.countries[selectedCountryKey];
      if (countryInfo && countryInfo.job_boards.length > 0) {
        setSelectedBoard(countryInfo.job_boards[0]);
      } else {
        setSelectedBoard("");
      }
    }
  }, [selectedCountryKey, countriesData]);

  const getSpiderName = (info: CountryInfo, board: string): string => {
    const matching = info.spiders.find((s) => s.toLowerCase().includes(board.toLowerCase()));
    return matching || board;
  };

  const handleTrigger = async (countryKey: string, board: string) => {
    if (!countriesData) return;

    const countryInfo = countriesData.countries[countryKey];
    if (!countryInfo) return;

    const spiderName = getSpiderName(countryInfo, board);
    const countryDisplayName = countryInfo.name;

    const historyId = Math.random().toString(36).substring(2, 9);
    const newHistoryItem: HistoryItem = {
      id: historyId,
      time: new Date().toLocaleTimeString(),
      country: countryDisplayName,
      board: board,
      spider: spiderName,
      status: "loading",
      message: "Sending trigger...",
    };

    setHistory((prev) => [newHistoryItem, ...prev]);

    try {
      const response = await postSubAggregate(countryDisplayName, spiderName);
      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId
            ? { ...item, status: "success", message: response.message || "Scraper triggered successfully." }
            : item
        )
      );
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to trigger scraper";
      setHistory((prev) =>
        prev.map((item) =>
          item.id === historyId ? { ...item, status: "error", message: errMsg } : item
        )
      );
    }
  };

  const handleManualFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCountryKey || !selectedBoard || triggering) return;

    setTriggering(true);
    await handleTrigger(selectedCountryKey, selectedBoard);
    setTriggering(false);
  };

  return (
    <div className="jobdork">
      <TopNav />

      <div className="jd-control-page">
        <div className="jd-page-header">
          <h1>Scraper Control Panel</h1>
          <p>
            Manually run individual spiders for specific countries to ingest job data into the database.
          </p>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 0" }}>
            <div className="jd-progress" style={{ margin: "20px auto", width: "120px" }} />
            <p className="mono" style={{ color: "var(--jd-muted)" }}>Loading supported countries and job boards...</p>
          </div>
        ) : error ? (
          <div className="jd-card" style={{ textAlign: "center", border: "1px solid var(--jd-red)" }}>
            <h3 style={{ color: "var(--jd-red)", marginBottom: "12px", fontFamily: "Sora" }}>Failed to Connect</h3>
            <p style={{ color: "var(--jd-muted)", marginBottom: "20px" }}>{error}</p>
            <button className="jd-btn" onClick={fetchCountries}>
              Retry Connection
            </button>
          </div>
        ) : (
          <div className="jd-grid-2">
            <div>
              <div className="jd-card">
                <h3 style={{ margin: "0 0 20px", fontFamily: "Sora", fontWeight: 600 }}>Manual Scraper Trigger</h3>
                <form onSubmit={handleManualFormSubmit}>
                  <div className="jd-form-group">
                    <label htmlFor="country-select">Country</label>
                    <select
                      id="country-select"
                      value={selectedCountryKey}
                      onChange={(e) => setSelectedCountryKey(e.target.value)}
                    >
                      {countriesData &&
                        Object.entries(countriesData.countries).map(([key, info]) => (
                          <option key={key} value={key}>
                            {(COUNTRY_FLAGS[key] || "🌐") + " " + info.name}
                          </option>
                        ))}
                    </select>
                  </div>

                  <div className="jd-form-group">
                    <label htmlFor="board-select">Job Board / Platform</label>
                    <select
                      id="board-select"
                      value={selectedBoard}
                      onChange={(e) => setSelectedBoard(e.target.value)}
                      disabled={
                        !selectedCountryKey ||
                        !countriesData?.countries[selectedCountryKey]?.job_boards?.length
                      }
                    >
                      {selectedCountryKey &&
                        countriesData?.countries[selectedCountryKey]?.job_boards.map((board) => (
                          <option key={board} value={board}>
                            {board.toUpperCase()}
                          </option>
                        ))}
                    </select>
                  </div>

                  {selectedCountryKey && selectedBoard && countriesData && (
                    <p className="mono" style={{ color: "var(--jd-muted)", fontSize: "11px", marginBottom: "20px" }}>
                      Target Spider:{" "}
                      <span style={{ color: "var(--jd-cyan)" }}>
                        {getSpiderName(countriesData.countries[selectedCountryKey], selectedBoard)}
                      </span>
                    </p>
                  )}

                  <button
                    type="submit"
                    className="jd-btn primary"
                    style={{ width: "100%", justifyContent: "center" }}
                    disabled={triggering || !selectedCountryKey || !selectedBoard}
                  >
                    {triggering ? "Initiating Scraper..." : "Run Spider Scraper"}
                  </button>
                </form>
              </div>

              {/* Real-time trigger history */}
              <div className="jd-history-panel">
                <div className="jd-history-title">
                  <span>⚡</span> Trigger Activity Logs
                </div>
                {history.length === 0 ? (
                  <p className="mono" style={{ color: "var(--jd-muted-2)", textAlign: "center", margin: "20px 0" }}>
                    No scraper triggers executed in this session.
                  </p>
                ) : (
                  <div className="jd-history-list">
                    {history.map((item) => (
                      <div key={item.id} className={`jd-history-item ${item.status}`}>
                        <div>
                          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                            <span className="time">[{item.time}]</span>
                            <span style={{ fontWeight: 600 }}>{item.country}</span>
                            <span style={{ color: "var(--jd-muted)" }}>→</span>
                            <span className="mono" style={{ color: "var(--jd-cyan)" }}>
                              {item.spider}
                            </span>
                          </div>
                          <div style={{ color: "var(--jd-muted-2)", marginTop: "4px", fontSize: "11px" }}>
                            {item.message}
                          </div>
                        </div>
                        <div>
                          {item.status === "loading" && (
                            <span style={{ color: "var(--jd-amber)" }}>● Pending</span>
                          )}
                          {item.status === "success" && (
                            <span style={{ color: "var(--jd-green)" }}>✓ Started</span>
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

            <div>
              <h3 style={{ margin: "0 0 20px", fontFamily: "Sora", fontWeight: 600 }}>Supported Spiders Mapping</h3>
              <div className="jd-grid-2" style={{ gap: "16px" }}>
                {countriesData &&
                  Object.entries(countriesData.countries).map(([key, info]) => {
                    const flag = COUNTRY_FLAGS[key] || "🌐";
                    return (
                      <div key={key} className="jd-country-card">
                        <div>
                          <div className="header">
                            <span className="flag">{flag}</span>
                            <span className="name">{info.name}</span>
                          </div>

                          <div className="spiders-list">
                            {info.spiders.map((spider) => (
                              <span key={spider} className="spider-badge">
                                {spider}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="actions">
                          {info.job_boards.map((board) => (
                            <div key={board} className="jd-board-row">
                              <span className="board-name">{board}</span>
                              <button
                                className="jd-btn primary btn-trigger"
                                onClick={() => handleTrigger(key, board)}
                              >
                                Trigger
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
