export interface FormState {
  keywords: string[];
  countries: string[];
  company: string | null;
  remote: boolean | null;
  limit: number;
  offset: number;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  url: string;
  description: string;
  location: string;
  salary: string;
  source: string;
  site: string;
  tags: string[];
  scraped_at: string;
  // compatibility fallbacks
  easy_apply?: boolean;
  job_type?: string;
  job_level?: string;
}

export interface JobBoard {
  name: string;
  jobs: Job[];
}

export interface CountryGroup {
  country: string;
  job_boards: JobBoard[];
}

export interface PaginatedSearchResponse {
  total: number;
  limit: number;
  offset: number;
  results: CountryGroup[];
}

