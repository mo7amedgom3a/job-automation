try:
    from scraper_api.parser import JobResultParser
except ModuleNotFoundError:
    from parser import JobResultParser


def test_is_specific_job_url_linkedin() -> None:
    """Verify that only specific LinkedIn job postings are allowed."""
    parser = JobResultParser()
    
    # Valid individual job post URL
    assert parser._is_specific_job_url("https://www.linkedin.com/jobs/view/123456789") is True
    assert parser._is_specific_job_url("https://eg.linkedin.com/jobs/view/987654321/") is True
    
    # Invalid LinkedIn landing/search/directory URLs
    assert parser._is_specific_job_url("https://www.linkedin.com/jobs/devops-jobs-worldwide/") is False
    assert parser._is_specific_job_url("https://www.linkedin.com/jobs/search/?keywords=devops") is False
    assert parser._is_specific_job_url("https://www.linkedin.com/jobs/collections/12345/") is False


def test_is_specific_job_url_indeed() -> None:
    """Verify that only specific Indeed job postings are allowed."""
    parser = JobResultParser()
    
    # Valid individual job post URL
    assert parser._is_specific_job_url("https://www.indeed.com/viewjob?jk=12345abcde") is True
    assert parser._is_specific_job_url("https://www.indeed.com/rc/clk?jk=12345abcde") is True
    
    # Invalid Indeed landing/search URLs
    assert parser._is_specific_job_url("https://www.indeed.com/jobs?q=devops") is False


def test_is_specific_job_url_lever() -> None:
    """Verify that only specific Lever job postings are allowed."""
    parser = JobResultParser()
    
    # Valid individual job post URL (segment count >= 2)
    assert parser._is_specific_job_url("https://jobs.lever.co/google/123456-abcdef") is True
    
    # Invalid Lever company landing URL
    assert parser._is_specific_job_url("https://jobs.lever.co/google") is False
    assert parser._is_specific_job_url("https://jobs.lever.co/google/") is False


def test_is_specific_job_url_greenhouse() -> None:
    """Verify that only specific Greenhouse job postings are allowed."""
    parser = JobResultParser()
    
    # Valid individual job post URL
    assert parser._is_specific_job_url("https://boards.greenhouse.io/company/jobs/123456") is True
    
    # Invalid Greenhouse company landing URL
    assert parser._is_specific_job_url("https://boards.greenhouse.io/company") is False
    assert parser._is_specific_job_url("https://boards.greenhouse.io/company/") is False


def test_parse_one_rejects_landing_pages() -> None:
    """Verify that the parser pipeline rejects raw landing page results."""
    parser = JobResultParser()
    
    # Landing page simulation should return None
    raw_landing = {
        "href": "https://www.linkedin.com/jobs/devops-jobs-worldwide/",
        "title": "361,000+ Devops jobs",
        "body": "Today’s top 361,000+ Devops jobs. Leverage your professional network, and get hired.",
    }
    assert parser._parse_one(raw_landing) is None
    
    # Specific job simulation should parse successfully
    raw_job = {
        "href": "https://www.linkedin.com/jobs/view/123456789",
        "title": "DevOps Engineer at Money Fellows",
        "body": "Money Fellows is hiring a DevOps Engineer in Cairo. Apply now!",
    }
    parsed = parser._parse_one(raw_job)
    assert parsed is not None
    assert parsed["title"] == "DevOps Engineer"
    assert parsed["company"] == "Money Fellows"


def test_parse_one_rejects_ad_networks() -> None:
    """Verify that search engine ad clicks and tracking links are strictly rejected."""
    parser = JobResultParser()
    
    # Simulating a Bing ad-click promotion result
    raw_ad = {
        "href": "https://www.bing.com/aclick?ld=e8KwD_hDSqvuupdMBmAVg3PjVUCUxTVnnL_...&u=https://www.indeed.com/jobs",
        "title": "Discover Remote Jobs Now",
        "body": "Search for job opportunities by experience, location, salary, & more.",
        "_dork_site": "linkedin.com/jobs"
    }
    assert parser._parse_one(raw_ad) is None


def test_parse_one_enforces_dork_site_match() -> None:
    """Verify that results are rejected if the URL doesn't match the searched dork site."""
    parser = JobResultParser()
    
    # Query was site:linkedin.com but search engine returned a mismatched URL
    raw_mismatched = {
        "href": "https://jobs.lever.co/company/job-id",
        "title": "Software Engineer",
        "body": "We are hiring a software engineer.",
        "_dork_site": "linkedin.com/jobs"
    }
    assert parser._parse_one(raw_mismatched) is None
    
    # Valid matching URL
    raw_matching = {
        "href": "https://www.linkedin.com/jobs/view/123456789",
        "title": "Software Engineer at Google",
        "body": "Google is hiring a Software Engineer.",
        "_dork_site": "linkedin.com/jobs"
    }
    assert parser._parse_one(raw_matching) is not None
