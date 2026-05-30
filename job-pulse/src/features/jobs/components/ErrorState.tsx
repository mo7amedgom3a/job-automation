export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="jd-error">
      <h3>Search failed</h3>
      <div className="msg">{message}</div>
      <p className="mono" style={{ fontSize: 11, color: "var(--jd-muted)", marginTop: 16 }}>
        Tip: the API host must be reachable from this browser. If you're running the backend on localhost, open this app from the same machine, or expose it via a tunnel (ngrok / cloudflared) and update the API base URL in the top bar.
      </p>
      <div style={{ marginTop: 18 }}>
        <button className="jd-btn primary" onClick={onRetry}>Retry</button>
      </div>
    </div>
  );
}
