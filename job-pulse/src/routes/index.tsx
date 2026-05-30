import { createFileRoute } from "@tanstack/react-router";
import { JobDorkApp } from "@/features/jobs/JobDorkApp";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "JobDork — Multi-source job search" },
      { name: "description", content: "Search LinkedIn, Indeed, Glassdoor, Google Jobs and ZipRecruiter — simultaneously." },
      { property: "og:title", content: "JobDork — Multi-source job search" },
      { property: "og:description", content: "Concurrent scraping across the major job boards in one query." },
    ],
  }),
  component: JobDorkApp,
});
