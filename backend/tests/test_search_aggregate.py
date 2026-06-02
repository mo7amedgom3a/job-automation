import pytest
import json
import hashlib
from typing import Any

from models.job import SearchRequest
from routes.search import search_aggregate
from cache.cache import DeduplicationCache
from repository.jobs import JobRepository
from services.orchestrator import JobOrchestrator


@pytest.mark.asyncio
async def test_search_aggregate_cache_miss_saves_and_caches(mocker: Any) -> None:
    # 1. Arrange mocks
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    # Orchestrate returns results dictionary
    mock_orchestrator.orchestrate = mocker.AsyncMock(return_value={
        "linkedin": [
            {"url": "https://linkedin.com/jobs/view/1", "title": "Staff Backend Engineer", "company": "Company A"}
        ],
        "indeed": [],
        "google": []
    })

    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_cache.get_value.return_value = None  # Cache miss

    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.fingerprint.return_value = "fingerprint_1"

    req = SearchRequest(keywords=["backend"], max_results=10)

    # 2. Act
    results = await search_aggregate(
        req=req,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    # 3. Assert
    assert len(results) == 1
    assert results[0]["title"] == "Staff Backend Engineer"
    assert results[0]["site"] == "linkedin"

    # Verify live orchestrate was called
    mock_orchestrator.orchestrate.assert_called_once_with(req)

    # Verify job was saved to DB
    mock_repository.save_job.assert_called_once()
    saved_job_arg = mock_repository.save_job.call_args[0][0]
    assert saved_job_arg["title"] == "Staff Backend Engineer"

    # Verify cache write (1 hour TTL)
    mock_cache.set_value.assert_called_once()
    set_key_arg = mock_cache.set_value.call_args[0][0]
    set_val_arg = mock_cache.set_value.call_args[0][1]
    set_ttl_arg = mock_cache.set_value.call_args[0][2]
    
    assert set_key_arg.startswith("aggregate:cache:")
    assert json.loads(set_val_arg) == ["fingerprint_1"]
    assert set_ttl_arg == 3600


@pytest.mark.asyncio
async def test_search_aggregate_cache_hit_retrieves_from_db(mocker: Any) -> None:
    # 1. Arrange mocks
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)

    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_cache.get_value.return_value = json.dumps(["fingerprint_1", "fingerprint_2"])

    mock_repository = mocker.MagicMock(spec=JobRepository)
    # Get jobs by fingerprint returns database rows
    mock_repository.get_jobs_by_fingerprints.return_value = [
        {
            "fingerprint": "fingerprint_2",
            "title": "Engineer B",
            "company": "Company B",
            "url": "https://indeed.com/view/2",
            "description": "Desc B",
            "location": "Loc B",
            "salary": "100k",
            "source": "indeed",
            "tags": "tags1,tags2",
            "scraped_at": "2026-06-02T20:00:00"
        },
        {
            "fingerprint": "fingerprint_1",
            "title": "Engineer A",
            "company": "Company A",
            "url": "https://linkedin.com/jobs/view/1",
            "description": "Desc A",
            "location": "Loc A",
            "salary": "120k",
            "source": "linkedin",
            "tags": "tags3",
            "scraped_at": "2026-06-02T20:00:00"
        }
    ]

    req = SearchRequest(keywords=["backend"], max_results=10)

    # 2. Act
    results = await search_aggregate(
        req=req,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    # 3. Assert
    # Verify live orchestrate was NOT called
    mock_orchestrator.orchestrate.assert_not_called()
    mock_repository.get_jobs_by_fingerprints.assert_called_once_with(["fingerprint_1", "fingerprint_2"])

    assert len(results) == 2
    # Check that they maintain cached order (fingerprint_1 first, then fingerprint_2)
    assert results[0]["title"] == "Engineer A"
    assert results[0]["site"] == "linkedin"
    assert results[0]["tags"] == ["tags3"]
    assert results[1]["title"] == "Engineer B"
    assert results[1]["site"] == "indeed"
    assert results[1]["tags"] == ["tags1", "tags2"]


@pytest.mark.asyncio
async def test_search_aggregate_reset_cache(mocker: Any) -> None:
    mock_orchestrator = mocker.MagicMock(spec=JobOrchestrator)
    mock_orchestrator.orchestrate = mocker.AsyncMock(return_value={"linkedin": [], "indeed": [], "google": []})
    mock_cache = mocker.MagicMock(spec=DeduplicationCache)
    mock_repository = mocker.MagicMock(spec=JobRepository)

    req = SearchRequest(keywords=["backend"], reset_cache=True)

    await search_aggregate(
        req=req,
        orchestrator=mock_orchestrator,
        cache=mock_cache,
        repository=mock_repository
    )

    mock_cache.clear.assert_called_once()
    mock_cache.delete.assert_called_once()
