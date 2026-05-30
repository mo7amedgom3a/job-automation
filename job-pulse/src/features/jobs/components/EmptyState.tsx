export function EmptyState({ onAdjust }: { onAdjust: () => void }) {
  return (
    <div className="jd-empty">
      <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ opacity: .8 }}>
        <circle cx="28" cy="28" r="16" stroke="#00d4ff" strokeWidth="2.5" />
        <line x1="40" y1="40" x2="54" y2="54" stroke="#00d4ff" strokeWidth="2.5" strokeLinecap="round" />
        <text x="28" y="33" textAnchor="middle" fill="#00d4ff" fontFamily="DM Mono" fontSize="14" fontWeight="700">?</text>
      </svg>
      <h3>No jobs found</h3>
      <p className="mono" style={{ fontSize: 12 }}>Try broader keywords, more platforms, or a longer time window.</p>
      <div style={{ marginTop: 18 }}>
        <button className="jd-btn primary" onClick={onAdjust}>Adjust Search</button>
      </div>
    </div>
  );
}
