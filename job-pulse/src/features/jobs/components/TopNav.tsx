import { useEffect, useRef, useState } from "react";
import { getApiBase, pingApi, setApiBase } from "../api";

export function TopNav() {
  const [up, setUp] = useState<boolean | null>(null);
  const [open, setOpen] = useState(false);
  const [base, setBase] = useState(getApiBase());
  const popRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    let ctrl: AbortController | null = null;
    const tick = async () => {
      ctrl?.abort();
      ctrl = new AbortController();
      const ok = await pingApi(ctrl.signal);
      if (!cancelled) setUp(ok);
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => { cancelled = true; clearInterval(id); ctrl?.abort(); };
  }, [base]);

  return (
    <div className="jd-nav">
      <div className="jd-logo">
        <span className="icon">◈</span>
        <span><span className="muted">job</span><span className="accent">dork</span></span>
      </div>
      <div className={`jd-status ${up === false ? "is-down" : ""}`}>
        <span className="dot" />
        <span className="mono">{up === false ? "Offline" : up === null ? "Checking…" : "Live"}</span>
        <button className="gear mono" onClick={() => setOpen((v) => !v)} title="API base URL">⚙</button>
      </div>
      {open && (
        <div className="jd-api-pop" ref={popRef}>
          <label>API Base URL</label>
          <input
            className="jd-input mono"
            value={base}
            onChange={(e) => setBase(e.target.value)}
            placeholder="http://127.0.0.1:8000"
          />
          <p className="mono" style={{ color: "var(--jd-muted)", fontSize: 11, marginTop: 8 }}>
            Must be reachable from this browser and serve CORS for this origin.
          </p>
          <div className="row">
            <button className="jd-btn" onClick={() => setOpen(false)}>Cancel</button>
            <button
              className="jd-btn primary"
              onClick={() => { setApiBase(base); setOpen(false); }}
            >Save</button>
          </div>
        </div>
      )}
    </div>
  );
}
