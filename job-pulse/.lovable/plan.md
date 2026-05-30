# JobDork — Build Plan

A single-page React app (TanStack Start) implementing a multi-source job search UI per your spec. Dark editorial aesthetic, Sora + DM Mono typography, electric cyan / amber accents.

## Heads-up before we build

- **API host `http://localhost:8000`** only works when you run the backend on your own machine *and* open the app from that same machine. The Lovable preview (and any published URL) won't reach your localhost, and the browser will also block it as mixed content over https. I'll make the base URL configurable via a small in-app setting (stored in `localStorage`, default `http://localhost:8000`) so you can point it at a tunneled URL (ngrok/cloudflared) when testing remotely. Tell me if you'd rather hardcode it.
- The backend must send permissive CORS headers for the preview origin, otherwise the browser will block the POST. Not something I can fix from the frontend.

## Scope

### Routes
- `/` — single page hosting both Search and Results views, toggled by state (no separate route; matches "single-page application" in spec).
- Update `__root.tsx` head with title "JobDork — Multi-source job search" and the Google Fonts `<link>` for Sora + DM Mono.

### File structure
```
src/
  routes/
    index.tsx                 # hosts <JobDorkApp />
  features/jobs/
    JobDorkApp.tsx            # top-level state machine (idle | loading | results | error)
    api.ts                    # postJobSearch(payload) + types
    types.ts                  # SearchPayload, JobResult, FormState
    presets.ts                # the 3 quick-start presets
    utils.ts                  # relative time, currency symbol, salary formatter, monogram color
    components/
      TopNav.tsx              # logo + API status dot
      SearchView.tsx          # hero + form + presets
      ResultsView.tsx         # two-panel layout
      SearchForm.tsx          # full form (Rows 1-5 + Advanced)
      KeywordTagInput.tsx
      PlatformChips.tsx
      WorkTypeTabs.tsx
      JobTypeTabs.tsx
      CountriesCombobox.tsx
      PostedWithinSelect.tsx
      MaxResultsSlider.tsx
      AdvancedOptions.tsx
      PresetChips.tsx
      ResultsToolbar.tsx      # count, grid/list toggle, sort
      ActiveFiltersBar.tsx
      FilterSidebar.tsx       # company/location/remote/salary/level/function
      JobCard.tsx             # grid + list variants
      SkeletonGrid.tsx
      EmptyState.tsx
      ErrorState.tsx
      MobileFiltersDrawer.tsx
  styles.css                  # add design tokens + keyframes (see Technical)
```

### State model (in `JobDorkApp`)
- `formState`: keywords, jobSites, workType ("remote"|"onsite"|"both"), onsiteCity, jobType, countries, postedWithin (encodes recent_hours OR days_back), maxResults, easyApply, linkedinFetchDescription, distance, enforceAnnualSalary, googleSearchTerm.
- `view`: "search" | "results".
- `request`: { status: "idle"|"loading"|"success"|"error", data: JobResult[], error?: string }.
- `clientFilters`: companies[], locations[], remoteOnly, salaryRange, levels[], functions[].
- `sort`: "date"|"salary"|"company". `layout`: "grid"|"list".

### Payload mapping (`api.ts`)
Build per spec: `job_sites` mapped from chip ids to domain strings (`linkedin.com/jobs`, etc.). `location` resolves from workType (`"remote"` | onsiteCity | `null`). `recent_hours`/`days_back` set mutually exclusively based on postedWithin selection. `distance` only sent for onsite. Omit empty optional fields as `null`.

### Results processing
- Normalize each job: parse numeric salary fields, derive `relativeDate(date_posted)`, hide empty values gracefully.
- `useMemo` for filtered+sorted list; client-side filters operate on cached array.
- Unique companies/locations/levels/functions derived for sidebar.
- Salary slider min/max computed from non-empty `min_amount`/`max_amount`.

### Card variants
- Grid (2-col ≥1024px) — compact, no description.
- List (1-col) — adds 120-char description preview with "Read more" expand. Markdown via a tiny regex formatter (no extra dep) for **bold**, bullets, line breaks.

### States
- Loading: 6 shimmer skeleton cards + top progress bar (cyan, animated `translateX`).
- Empty: SVG magnifier+? illustration, "Adjust Search" button returns to search view.
- Error: red-tinted card, message, Retry button (re-submits last payload).

### Responsive
- ≥1024px: two-panel layout.
- 768–1023px: single column, sidebar becomes drawer.
- <768px: single-column cards, floating "Filters" FAB opens slide-up drawer; search form stacks all columns.

## Technical details

- **Styling**: per spec, no Tailwind/shadcn. Use plain CSS classes in a project-scoped stylesheet `src/features/jobs/jobdork.css` imported by `JobDorkApp`. Design tokens (`--jd-bg`, `--jd-surface`, `--jd-cyan`, `--jd-amber`, `--jd-text`, `--jd-muted`, `--jd-border`, `--jd-radius`) defined under a `.jobdork` root class so they don't collide with existing shadcn tokens. Keyframes (`shimmer`, `card-in`, `pulse-dot`, `progress-slide`) in same file.
- **Fonts**: add `<link rel="preconnect">` + Google Fonts stylesheet via `__root.tsx` `head().links`.
- **No new deps**: react-markdown intentionally skipped — implement small `renderLite(md)` for bold/bullets/newlines.
- **API base URL**: `getApiBase()` reads `localStorage.jobdork_api_base` or defaults to `http://localhost:8000`. Small gear in TopNav opens a tiny popover to edit it. "API Status" dot pings `GET {base}/` (or a HEAD on the search path) on mount and every 30s to flip green/red.
- **Networking**: `fetch` + `AbortController` so a new search cancels the prior one. Surface non-2xx as error state.
- **Accessibility**: labels associated with controls, keyboard-removable tags, focus rings in cyan, `aria-live="polite"` on results count.

## Out of scope (will not do unless you ask)
- Saving searches / auth / persistence beyond the API base URL.
- Pagination (the API returns a full array; we render all with virtualization only if needed later).
- Backend changes or CORS proxy.

Confirm and I'll build it.
