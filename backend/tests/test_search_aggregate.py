import pytest
import json
from typing import Any

from models.job import SearchRequest, JobSearchRequest, SubAggregateRequest
from routes.search import search_aggregate, run_full_aggregation, search_jobs, search_sub_aggregate, run_sub_aggregation, find_matching_spiders
from cache.cache import DeduplicationCache
from repository.jobs import JobRepository
from services.orchestrator import JobOrchestrator
from config.settings import DEFAULT_SEARCH_LIMIT


@pytest.mark.asyncio
async def test_search_aggregate_triggers_background_task(mocker: Any) -> None:
    # Arrange mocks
    mock_bg_tasks = mocker.MagicMock()
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)

    # Act
    response = await search_aggregate(
        background_tasks=mock_bg_tasks,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    # Assert
    assert response == {"status": "initiated", "message": "Aggregation process started in the background."}
    mock_bg_tasks.add_task.assert_called_once_with(
        run_full_aggregation,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )


@pytest.mark.asyncio
async def test_run_full_aggregation(mocker: Any) -> None:
    # Arrange mocks
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_orchestrator.orchestrate = mocker.AsyncMock(return_value={
        "linkedin": [
            {"url": "https://linkedin.com/jobs/view/1", "title": "Staff Backend Engineer", "company": "Company A"}
        ],
        "indeed": [],
        "google": []
    })

    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.fingerprint.return_value = "fingerprint_1"

    # Act
    await run_full_aggregation(
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    # Assert
    mock_orchestrator.orchestrate.assert_called_once()
    mock_repository.save_job.assert_called_once()
    mock_cache.set_value.assert_called_once()

    set_key_arg = mock_cache.set_value.call_args[0][0]
    set_val_arg = mock_cache.set_value.call_args[0][1]
    set_ttl_arg = mock_cache.set_value.call_args[0][2]

    assert set_key_arg == "aggregate:latest"
    assert json.loads(set_val_arg) == ["fingerprint_1"]
    assert set_ttl_arg == 3600


@pytest.mark.asyncio
async def test_search_jobs_endpoint_with_filters(mocker: Any) -> None:
    # Arrange mocks
    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.search_jobs.return_value = (
        [
            {
                "fingerprint": "fingerprint_1",
                "title": "Engineer A",
                "company": "Company A",
                "url": "https://linkedin.com/jobs/view/1",
                "description": "Desc A",
                "location": "Remote",
                "salary": "120k",
                "source": "linkedin_eg",
                "tags": "tags1",
                "scraped_at": "2026-06-02T20:00:00"
            }
        ],
        1
    )

    req = JobSearchRequest(keywords=["Engineer"], remote=True)

    # Act
    results = await search_jobs(req=req, repository=mock_repository)

    # Assert
    mock_repository.search_jobs.assert_called_once_with(
        keywords=["Engineer"],
        countries=None,
        company=None,
        remote=True,
        limit=DEFAULT_SEARCH_LIMIT,
        offset=0
    )

    assert results["total"] == 1
    assert results["limit"] == DEFAULT_SEARCH_LIMIT
    assert results["offset"] == 0
    assert len(results["results"]) == 1
    assert results["results"][0]["country"] == "Egypt"
    assert results["results"][0]["job_boards"][0]["name"] == "linkedin"
    assert results["results"][0]["job_boards"][0]["jobs"][0]["title"] == "Engineer A"


@pytest.mark.asyncio
async def test_search_jobs_endpoint_unrestricted(mocker: Any) -> None:
    # Arrange mocks for unrestricted query
    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.search_jobs.return_value = (
        [
            {
                "fingerprint": "fingerprint_1",
                "title": "Engineer Remote",
                "company": "Company A",
                "url": "https://linkedin.com/jobs/view/1",
                "description": "Desc A",
                "location": "Remote",
                "salary": "120k",
                "source": "linkedin_eg",
                "tags": "tags1",
                "scraped_at": "2026-06-02T20:00:00"
            },
            {
                "fingerprint": "fingerprint_2",
                "title": "Engineer Onsite",
                "company": "Company B",
                "url": "https://indeed.com/view/2",
                "description": "Desc B",
                "location": "Berlin, Germany",
                "salary": "140k",
                "source": "indeed_germany",
                "tags": "tags2",
                "scraped_at": "2026-06-02T21:00:00"
            }
        ],
        2
    )

    req = JobSearchRequest(keywords=["Engineer"])  # country and remote are None

    # Act
    results = await search_jobs(req=req, repository=mock_repository)

    # Assert
    mock_repository.search_jobs.assert_called_once_with(
        keywords=["Engineer"],
        countries=None,
        company=None,
        remote=None,
        limit=DEFAULT_SEARCH_LIMIT,
        offset=0
    )

    # Both jobs should be kept because remote is None (no filtering by remote),
    # and they should be grouped under Egypt and Germany respectively.
    assert results["total"] == 2
    assert results["limit"] == DEFAULT_SEARCH_LIMIT
    assert results["offset"] == 0
    assert len(results["results"]) == 2
    countries = {r["country"] for r in results["results"]}
    assert countries == {"Egypt", "Germany"}


def test_find_matching_spiders() -> None:
    # Test Egypt + LinkedIn -> linkedin_eg
    spiders = find_matching_spiders("egypt", "linkedin")
    assert "linkedin_eg" in spiders
    assert "indeed_eg" not in spiders

    # Test Egypt + Indeed -> indeed_eg
    spiders = find_matching_spiders("egypt", "indeed")
    assert "indeed_eg" in spiders
    assert "linkedin_eg" not in spiders

    # Test Germany + LinkedIn -> linkedin_germany
    spiders = find_matching_spiders("germany", "linkedin")
    assert "linkedin_germany" in spiders

    # Test invalid country
    spiders = find_matching_spiders("nonexistent", "linkedin")
    assert not spiders


@pytest.mark.asyncio
async def test_search_sub_aggregate_triggers_background_task(mocker: Any) -> None:
    mock_bg_tasks = mocker.MagicMock()
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)

    req = SubAggregateRequest(country="egypt", job_board="linkedin")

    response = await search_sub_aggregate(
        req=req,
        background_tasks=mock_bg_tasks,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    assert response == {
        "status": "initiated",
        "message": "Sub-aggregation process started in the background for linkedin in egypt."
    }
    mock_bg_tasks.add_task.assert_called_once_with(
        run_sub_aggregation,
        country="egypt",
        job_board="linkedin",
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )


@pytest.mark.asyncio
async def test_run_sub_aggregation(mocker: Any) -> None:
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_orchestrator.max_concurrent_spiders = 2
    mock_orchestrator.spider_runner = mocker.MagicMock()
    
    mock_orchestrator.spider_runner.run = mocker.AsyncMock(return_value=[
        {
            "url": "https://linkedin.com/jobs/view/1",
            "title": "Egypt LinkedIn Job",
            "company": "Company Egypt",
            "location": "Cairo",
            "scraped_at": "2026-06-03T12:00:00"
        }
    ])
    
    mock_orchestrator._build_env_overrides = mocker.MagicMock(return_value={"SOME_ENV": "val"})

    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.fingerprint.return_value = "fingerprint_egy_li"

    await run_sub_aggregation(
        country="egypt",
        job_board="linkedin",
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    mock_orchestrator.spider_runner.run.assert_called_once()
    mock_repository.save_job.assert_called_once()
    mock_cache.set_value.assert_called_once()

    set_key_arg = mock_cache.set_value.call_args[0][0]
    set_val_arg = mock_cache.set_value.call_args[0][1]
    
    assert set_key_arg == "aggregate:sub:egypt:linkedin:latest"
    assert json.loads(set_val_arg) == ["fingerprint_egy_li"]


@pytest.mark.asyncio
async def test_run_sub_aggregation_uses_settings_keywords(mocker: Any) -> None:
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_orchestrator.max_concurrent_spiders = 1
    mock_orchestrator.spider_runner = mocker.MagicMock()
    mock_orchestrator.spider_runner.run = mocker.AsyncMock(return_value=[])

    mock_orchestrator._build_env_overrides = mocker.MagicMock(return_value={"SOME_ENV": "val"})

    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)

    # Mock SITES to return a specific SiteConfig for 'linkedin_eg'
    from config.settings import SiteConfig
    mock_site_cfg = SiteConfig(
        name="linkedin_eg",
        start_urls=["https://example.com"],
        keywords=["Django", "FastAPI"],
        enabled=True
    )
    mocker.patch("config.settings.SITES", [mock_site_cfg])

    await run_sub_aggregation(
        country="egypt",
        job_board="linkedin",
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    mock_orchestrator._build_env_overrides.assert_called_once()
    passed_keywords = mock_orchestrator._build_env_overrides.call_args[0][1]
    # Check that it resolved site-specific keywords from config
    assert passed_keywords == ["Django", "FastAPI"]


def test_fingerprint_dedup() -> None:
    job1 = {"title": "Backend Engineer", "company": "Google", "url": "https://google.com/1"}
    job2 = {"title": "backend engineer", "company": " google ", "url": "https://google.com/2"}
    
    fp1 = JobRepository.fingerprint(job1, source="linkedin")
    fp2 = JobRepository.fingerprint(job2, source="linkedin")
    assert fp1 == fp2
    
    fp3 = JobRepository.fingerprint(job1, source="indeed")
    assert fp1 != fp3
    
    job3 = {"title": "DevOps Engineer", "company": "Google"}
    fp4 = JobRepository.fingerprint(job3, source="linkedin")
    assert fp1 != fp4
