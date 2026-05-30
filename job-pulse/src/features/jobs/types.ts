export type SiteId = "linkedin" | "indeed" | "glassdoor" | "google" | "zip_recruiter";

export type WorkType = "remote" | "onsite" | "both";
export type JobTypeOption = "any" | "full-time" | "part-time" | "contract" | "internship";

export type PostedWithinKey = "24h" | "3d" | "7d" | "30d";

export interface FormState {
  keywords: string[];
  jobSites: SiteId[];
  workType: WorkType;
  onsiteCity: string;
  jobType: JobTypeOption;
  countries: string[];
  postedWithin: PostedWithinKey;
  maxResults: number;
  easyApply: boolean;
  strictCountry: boolean;
  linkedinFetchDescription: boolean;
  distance: number;
  enforceAnnualSalary: boolean;
  googleSearchTerm: string;
}

export interface SearchPayload {
  keywords: string[];
  job_sites: string[];
  location: string | null;
  countries: string[];
  job_type: string | null;
  recent_hours: number | null;
  days_back: number | null;
  max_results: number;
  easy_apply: boolean | null;
  strict_country: boolean | null;
  linkedin_fetch_description: boolean;
  distance: number | null;
  enforce_annual_salary: boolean | null;
  google_search_term: string | null;
}

export interface JobResult {
  id: string;
  site: string;
  job_url: string;
  job_url_direct: string;
  title: string;
  company: string;
  location: string;
  date_posted: string;
  job_type: string;
  salary_source: string;
  interval: string;
  min_amount: string | number;
  max_amount: string | number;
  currency: string;
  is_remote: boolean;
  job_level: string;
  job_function: string;
  listing_type: string;
  emails: string;
  description: string;
  company_industry: string;
  company_url: string;
  company_logo: string;
  company_url_direct: string;
  company_addresses: string;
  company_num_employees: string;
  company_revenue: string;
  company_description: string;
  skills: string;
  experience_range: string;
  company_rating: string;
  company_reviews_count: string;
  vacancy_count: string;
  work_from_home_type: string;
  easy_apply?: boolean;
}
