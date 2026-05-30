import type { FormState } from "./types";

export interface Preset {
  id: string;
  label: string;
  patch: Partial<FormState>;
}

export const PRESETS: Preset[] = [
  {
    id: "egypt-devops",
    label: "🌍 Egypt · DevOps · 24h",
    patch: {
      keywords: ["devops", "software engineer"],
      countries: ["egypt"],
      postedWithin: "24h",
      workType: "both",
      onsiteCity: "",
    },
  },
  {
    id: "me-remote-backend",
    label: "🌐 ME Remote · Backend · 24h",
    patch: {
      keywords: ["backend engineer", "python", "go"],
      countries: ["egypt", "saudi arabia", "uae", "qatar"],
      workType: "remote",
      postedWithin: "24h",
    },
  },
  {
    id: "cairo-onsite-frontend",
    label: "🏢 Cairo Onsite · Frontend · 72h",
    patch: {
      keywords: ["frontend developer"],
      countries: ["egypt"],
      workType: "onsite",
      onsiteCity: "Cairo",
      distance: 25,
      postedWithin: "3d",
    },
  },
];
