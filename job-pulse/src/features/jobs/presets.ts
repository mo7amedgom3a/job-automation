import type { FormState } from "./types";

export interface Preset {
  id: string;
  label: string;
  patch: Partial<FormState>;
}

export const PRESETS: Preset[] = [
  {
    id: "egypt-devops",
    label: "🌍 Egypt · DevOps",
    patch: {
      keywords: ["devops", "software engineer"],
      country: "egypt",
      remote: null,
      limit: 50,
      offset: 0,
    },
  },
  {
    id: "global-remote-backend",
    label: "🌐 Global Remote · Backend",
    patch: {
      keywords: ["backend engineer", "python", "go"],
      country: null,
      remote: true,
      limit: 50,
      offset: 0,
    },
  },
  {
    id: "germany-onsite-frontend",
    label: "🏢 Germany · Frontend",
    patch: {
      keywords: ["frontend developer", "react"],
      country: "germany",
      remote: false,
      limit: 50,
      offset: 0,
    },
  },
];
