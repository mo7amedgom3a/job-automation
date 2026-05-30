from unittest.mock import patch, MagicMock
import pytest
try:
    from scraper_api.searcher import JobSpySearcher
except ModuleNotFoundError:
    from searcher import JobSpySearcher


def test_country_normalization() -> None:
    """Verify that countries are correctly resolved to JobSpy casing."""
    searcher = JobSpySearcher()
    assert searcher.SUPPORTED_COUNTRIES["egypt"] == "Egypt"
    assert searcher.SUPPORTED_COUNTRIES["usa"] == "USA"
    assert searcher.SUPPORTED_COUNTRIES["united kingdom"] == "UK"
    assert searcher.SUPPORTED_COUNTRIES["uae"] == "United Arab Emirates"


@patch("jobspy.scrape_jobs")
def test_indeed_safeguards_easy_apply(mock_scrape_jobs: MagicMock) -> None:
    """Verify indeed limitations prioritizing easy_apply."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    # 1. Easy Apply True -> drops hours_old, job_type, is_remote
    searcher._scrape_site_sync(
        site="indeed",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="USA",
        job_type="fulltime",
        easy_apply=True,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs["easy_apply"] is True
    assert "hours_old" not in kwargs
    assert "job_type" not in kwargs
    assert "is_remote" not in kwargs


@patch("jobspy.scrape_jobs")
def test_indeed_safeguards_job_type_and_remote(mock_scrape_jobs: MagicMock) -> None:
    """Verify indeed limitations prioritizing job_type/is_remote when easy_apply is false/none."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    # 2. Easy Apply False, job_type/is_remote present -> drops hours_old
    searcher._scrape_site_sync(
        site="indeed",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="USA",
        job_type="fulltime",
        easy_apply=False,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("is_remote") is True
    assert kwargs.get("job_type") == "fulltime"
    assert "easy_apply" not in kwargs
    assert "hours_old" not in kwargs


@patch("jobspy.scrape_jobs")
def test_indeed_safeguards_hours_old(mock_scrape_jobs: MagicMock) -> None:
    """Verify indeed limitations fallbacks to hours_old when no easy_apply/job_type/is_remote present."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    # 3. No easy_apply/job_type/is_remote -> passes hours_old
    searcher._scrape_site_sync(
        site="indeed",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=False,
        country_indeed="Egypt",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("hours_old") == 24
    assert "easy_apply" not in kwargs
    assert "is_remote" not in kwargs
    assert "job_type" not in kwargs


@patch("jobspy.scrape_jobs")
def test_linkedin_safeguards_easy_apply(mock_scrape_jobs: MagicMock) -> None:
    """Verify linkedin limitations drop hours_old when easy_apply is True."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    searcher._scrape_site_sync(
        site="linkedin",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="worldwide",
        job_type="fulltime",
        easy_apply=True,
        linkedin_fetch_description=True,
        linkedin_company_ids=[12345],
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs["easy_apply"] is True
    assert "hours_old" not in kwargs
    # LinkedIn still receives is_remote, job_type, fetch description, etc.
    assert kwargs.get("is_remote") is True
    assert kwargs.get("job_type") == "fulltime"
    assert kwargs.get("linkedin_fetch_description") is True
    assert kwargs.get("linkedin_company_ids") == [12345]


@patch("jobspy.scrape_jobs")
def test_linkedin_safeguards_hours_old(mock_scrape_jobs: MagicMock) -> None:
    """Verify linkedin limitations keep hours_old when easy_apply is false/none."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    searcher._scrape_site_sync(
        site="linkedin",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="worldwide",
        job_type="fulltime",
        easy_apply=None,
        linkedin_fetch_description=True,
        linkedin_company_ids=[12345],
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("hours_old") == 24
    assert "easy_apply" not in kwargs
    assert kwargs.get("is_remote") is True
    assert kwargs.get("job_type") == "fulltime"


@patch("jobspy.scrape_jobs")
def test_google_safeguards_dynamic_terms(mock_scrape_jobs: MagicMock) -> None:
    """Verify google jobs dynamically compiles the search term if google_search_term is empty."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    searcher._scrape_site_sync(
        site="google",
        search_term="devops",
        location="San Francisco, CA",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="worldwide",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("google_search_term") == "devops jobs near San Francisco, CA since yesterday"


@patch("jobspy.scrape_jobs")
def test_linkedin_resolved_location(mock_scrape_jobs: MagicMock) -> None:
    """Verify that LinkedIn resolves the location correctly when a country filter is present."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    # 1. Location is "remote", country is "Egypt" (so country_indeed="Egypt")
    searcher._scrape_site_sync(
        site="linkedin",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="Egypt",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("location") == "Egypt"

    # 2. Location is empty, country is "Egypt" (so country_indeed="Egypt")
    searcher._scrape_site_sync(
        site="linkedin",
        search_term="devops",
        location="",
        results_wanted=10,
        hours_old=24,
        is_remote=False,
        country_indeed="Egypt",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("location") == "Egypt"

    # 3. Location is "Cairo", country is "Egypt"
    searcher._scrape_site_sync(
        site="linkedin",
        search_term="devops",
        location="Cairo",
        results_wanted=10,
        hours_old=24,
        is_remote=False,
        country_indeed="Egypt",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("location") == "Cairo"


@patch("jobspy.scrape_jobs")
def test_indeed_middle_east_resolved_location(mock_scrape_jobs: MagicMock) -> None:
    """Verify that Indeed resolves Middle East remote searches safely to country-wide without remote flag."""
    searcher = JobSpySearcher()
    mock_scrape_jobs.return_value = None
    
    # 1. Location is "remote", country is "Egypt"
    searcher._scrape_site_sync(
        site="indeed",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="Egypt",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("location") == "Egypt"
    assert "is_remote" not in kwargs

    # 2. Location is "remote", country is "Germany" (should still use normal remote filter)
    searcher._scrape_site_sync(
        site="indeed",
        search_term="devops",
        location="remote",
        results_wanted=10,
        hours_old=24,
        is_remote=True,
        country_indeed="Germany",
        job_type=None,
        easy_apply=None,
        linkedin_fetch_description=False,
        linkedin_company_ids=None,
        google_search_term=None,
        distance=None,
        proxies=None,
        enforce_annual_salary=None,
        user_agent=None,
        ca_cert=None,
        description_format="markdown",
    )
    
    _, kwargs = mock_scrape_jobs.call_args
    assert kwargs.get("location") == "remote"
    assert kwargs.get("is_remote") is True


