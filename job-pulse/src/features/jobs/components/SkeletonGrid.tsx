export function SkeletonGrid({ layout = "grid" as "grid" | "list" }) {
  return (
    <div className={`jd-cards ${layout}`}>
      {Array.from({ length: 6 }).map((_, i) => (
        <div className="jd-skel" key={i}>
          <div style={{ display: "flex", gap: 12 }}>
            <div className="jd-shim" style={{ width: 40, height: 40, borderRadius: 8 }} />
            <div style={{ flex: 1 }}>
              <div className="jd-shim" style={{ height: 14, width: "70%" }} />
              <div className="jd-shim" style={{ height: 10, width: "40%", marginTop: 8 }} />
            </div>
            <div className="jd-shim" style={{ height: 18, width: 64, borderRadius: 999 }} />
          </div>
          <div className="jd-shim" style={{ height: 10, width: "30%", marginTop: 16 }} />
          <div className="jd-shim" style={{ height: 10, width: "55%", marginTop: 6 }} />
        </div>
      ))}
    </div>
  );
}
