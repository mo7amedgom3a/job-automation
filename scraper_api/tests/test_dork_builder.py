try:
    from scraper_api.dork_builder import DorkQueryBuilder
except ModuleNotFoundError:
    from dork_builder import DorkQueryBuilder


def test_linkedin_url_pattern_scoping() -> None:
    """Verify that LinkedIn search targets specific view URLs to avoid landing pages."""
    builder = DorkQueryBuilder()
    queries = builder.build(
        keywords=["devops"],
        sites=["linkedin.com/jobs"],
        location="onsite",
        countries=["egypt"],
    )
    
    assert len(queries) > 0
    for q_dict in queries:
        query_str = q_dict["query"]
        if q_dict["site"] == "linkedin.com/jobs":
            assert "site:linkedin.com/jobs/view" in query_str
            assert "site:linkedin.com/jobs " not in query_str


def test_location_filtering_onsite() -> None:
    """Verify that an onsite search does not generate remote or hybrid queries."""
    builder = DorkQueryBuilder()
    queries = builder.build(
        keywords=["devops"],
        sites=["linkedin.com/jobs"],
        location="onsite",
        countries=["egypt"],
    )
    
    assert len(queries) > 0
    for q_dict in queries:
        query_str = q_dict["query"]
        if q_dict["site"] != "multi-site":  # Strategy 4 might not use location
            assert '"remote"' not in query_str
            assert '"hybrid"' not in query_str


def test_location_filtering_remote() -> None:
    """Verify that a remote search generates remote queries."""
    builder = DorkQueryBuilder()
    queries = builder.build(
        keywords=["devops"],
        sites=["linkedin.com/jobs"],
        location="remote",
        countries=["egypt"],
    )
    
    assert len(queries) > 0
    for q_dict in queries:
        query_str = q_dict["query"]
        if q_dict["site"] != "multi-site":
            # Remote should be in the query
            assert '"remote"' in query_str
            assert '"hybrid"' not in query_str


def test_query_volume_reduction() -> None:
    """Verify that the number of generated queries is highly optimized (~33, compared to 123)."""
    builder = DorkQueryBuilder()
    queries = builder.build(
        keywords=["devops", "terraform", "kubernetes"],
        sites=["linkedin.com/jobs", "indeed.com/jobs", "lever.co", "greenhouse.io"],
        location="onsite",
        countries=["egypt"],
    )
    
    # Reduced from original 123 queries down to 33 queries.
    assert len(queries) <= 35


def test_queries_include_after_cutoff() -> None:
    """Verify all generated queries include a strict after: date cutoff."""
    builder = DorkQueryBuilder()
    queries = builder.build(
        keywords=["devops"],
        sites=["linkedin.com/jobs"],
        location="remote",
        countries=["egypt"],
        days_back=2,
    )

    assert len(queries) > 0
    for q_dict in queries:
        assert "after:" in q_dict["query"]
