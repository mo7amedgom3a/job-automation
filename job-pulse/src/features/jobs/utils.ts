export const isEmpty = (v: unknown) =>
  v === null || v === undefined || (typeof v === "string" && v.trim() === "");

export function relativeTime(iso: string): string {
  if (isEmpty(iso)) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  const diff = Date.now() - d.getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const days = Math.floor(h / 24);
  if (days < 7) return `${days}d ago`;
  const w = Math.floor(days / 7);
  if (w < 5) return `${w}w ago`;
  const mo = Math.floor(days / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.floor(days / 365)}y ago`;
}

export function currencySymbol(code: string): string {
  const map: Record<string, string> = {
    USD: "$", CAD: "C$", AUD: "A$", EUR: "€", GBP: "£", JPY: "¥",
    INR: "₹", AED: "AED ", SAR: "SAR ", EGP: "E£", QAR: "QAR ",
    KWD: "KD ", BHD: "BD ", OMR: "OMR ",
  };
  if (!code) return "$";
  return map[code.toUpperCase()] ?? `${code} `;
}

export function intervalLabel(interval: string): string {
  const i = (interval || "").toLowerCase();
  if (i.startsWith("year") || i === "yearly" || i === "yr") return "/ yr";
  if (i.startsWith("hour") || i === "hourly" || i === "hr") return "/ hr";
  if (i.startsWith("month") || i === "monthly" || i === "mo") return "/ mo";
  if (i.startsWith("week") || i === "weekly") return "/ wk";
  if (i.startsWith("day") || i === "daily") return "/ day";
  return "";
}

export function formatSalary(min: string | number, max: string | number, currency: string, interval: string): string | null {
  const toNum = (x: string | number) => {
    if (typeof x === "number") return isNaN(x) ? null : x;
    const t = (x || "").toString().trim();
    if (!t) return null;
    const n = parseFloat(t.replace(/[,\s]/g, ""));
    return isNaN(n) ? null : n;
  };
  const mn = toNum(min);
  const mx = toNum(max);
  if (mn == null && mx == null) return null;
  const sym = currencySymbol(currency);
  const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });
  const itv = intervalLabel(interval);
  if (mn != null && mx != null && mn !== mx) return `${sym}${fmt(mn)} – ${sym}${fmt(mx)} ${itv}`.trim();
  return `${sym}${fmt((mn ?? mx) as number)} ${itv}`.trim();
}

export function monogramColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return `hsl(${hue} 55% 32%)`;
}

export function monogram(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

// Minimal markdown renderer: **bold**, bullets, line breaks
export function renderLite(md: string): { __html: string } {
  const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
  let s = esc(md);
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // bullets
  const lines = s.split(/\r?\n/);
  const out: string[] = [];
  let inList = false;
  for (const line of lines) {
    const m = /^\s*[-*•]\s+(.*)/.exec(line);
    if (m) {
      if (!inList) { out.push("<ul>"); inList = true; }
      out.push(`<li>${m[1]}</li>`);
    } else {
      if (inList) { out.push("</ul>"); inList = false; }
      if (line.trim()) out.push(`<p>${line}</p>`);
    }
  }
  if (inList) out.push("</ul>");
  return { __html: out.join("") };
}

export function jobTypeLabel(t: string): string {
  const k = (t || "").toLowerCase().replace(/[\s_-]/g, "");
  if (k.startsWith("full")) return "Full-Time";
  if (k.startsWith("part")) return "Part-Time";
  if (k === "contract" || k === "contractor") return "Contract";
  if (k === "internship" || k === "intern") return "Internship";
  if (k === "temporary" || k === "temp") return "Temporary";
  return t || "";
}

export const SITE_DOMAIN: Record<string, string> = {
  linkedin: "linkedin.com/jobs",
  indeed: "indeed.com/jobs",
  glassdoor: "glassdoor.com",
  google: "google.com",
  zip_recruiter: "ziprecruiter.com",
};

export const SITE_LABEL: Record<string, string> = {
  linkedin: "LinkedIn",
  indeed: "Indeed",
  glassdoor: "Glassdoor",
  google: "Google Jobs",
  zip_recruiter: "ZipRecruiter",
};
