import pytest
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from models.job import DeleteOldJobsResponse
from repository.jobs import JobRepository
from routes.jobs import delete_old_jobs


@pytest.mark.asyncio
async def test_delete_old_jobs_endpoint(mocker) -> None:
    # Arrange
    mock_repository = mocker.MagicMock(spec=JobRepository)

    mock_deleted_rows = [
        {
            "id": 1,
            "fingerprint": "fingerprint_1",
            "title": "Old Backend Engineer",
            "company": "Legacy Corp",
            "url": "https://example.com/jobs/1",
            "description": "Maintain legacy systems",
            "location": "Cairo, Egypt",
            "tags": "python,django",
            "salary": "N/A",
            "source": "linkedin_eg",
            "scraped_at": datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
        }
    ]
    mock_repository.delete_old_jobs.return_value = mock_deleted_rows

    # Act
    response = await delete_old_jobs(
        days=2,
        hours=12,
        minutes=30,
        start_date=None,
        end_date=None,
        truncate=False,
        repository=mock_repository,
    )

    # Assert
    mock_repository.delete_old_jobs.assert_called_once_with(
        days=2,
        hours=12,
        minutes=30,
        start_date=None,
        end_date=None,
        truncate=False,
    )
    assert isinstance(response, DeleteOldJobsResponse)
    assert response.deleted_count == 1
    assert len(response.deleted_jobs) == 1

    job = response.deleted_jobs[0]
    assert job.id == hashlib.md5("https://example.com/jobs/1".encode()).hexdigest()
    assert job.title == "Old Backend Engineer"
    assert job.company == "Legacy Corp"
    assert job.url == "https://example.com/jobs/1"
    assert job.description == "Maintain legacy systems"
    assert job.location == "Cairo, Egypt"
    assert job.salary == "N/A"
    assert job.source == "linkedin_eg"
    assert job.site == "linkedin_eg"
    assert job.tags == ["python", "django"]
    assert job.scraped_at == "2026-06-01T10:00:00+00:00"


@pytest.mark.asyncio
async def test_delete_old_jobs_endpoint_range_and_truncate(mocker) -> None:
    # Arrange
    mock_repository = mocker.MagicMock(spec=JobRepository)
    mock_repository.delete_old_jobs.return_value = []

    # Act - range
    response = await delete_old_jobs(
        days=None,
        hours=None,
        minutes=None,
        start_date="2026-06-08T00:00:00Z",
        end_date="2026-06-08T23:59:59Z",
        truncate=False,
        repository=mock_repository,
    )

    # Assert - range call
    mock_repository.delete_old_jobs.assert_called_with(
        days=None,
        hours=None,
        minutes=None,
        start_date=datetime(2026, 6, 8, 0, 0, 0, tzinfo=timezone.utc),
        end_date=datetime(2026, 6, 8, 23, 59, 59, tzinfo=timezone.utc),
        truncate=False,
    )

    # Act - truncate
    await delete_old_jobs(
        days=None,
        hours=None,
        minutes=None,
        start_date=None,
        end_date=None,
        truncate=True,
        repository=mock_repository,
    )

    # Assert - truncate call
    mock_repository.delete_old_jobs.assert_called_with(
        days=None,
        hours=None,
        minutes=None,
        start_date=None,
        end_date=None,
        truncate=True,
    )


def test_delete_old_jobs_repository_method_relative_age(mocker) -> None:
    # Arrange
    repo = JobRepository(database_url="postgresql://test_user:test_password@localhost:5432/test_db")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_context = mocker.MagicMock()
    mock_context.__enter__.return_value = mock_conn
    mocker.patch.object(repo, "_connect", return_value=mock_context)

    # Act
    repo.delete_old_jobs(days=1, hours=6, minutes=30)

    # Assert
    mock_conn.execute.assert_called_once()
    query_str, params = mock_conn.execute.call_args[0]
    assert "DELETE FROM jobs WHERE scraped_at <" in query_str
    
    cutoff = params[0]
    assert isinstance(cutoff, datetime)
    time_diff = datetime.now(timezone.utc) - cutoff
    # 1 day + 6 hours + 30 mins = 30.5 hours = 109800 seconds
    assert 109700 < time_diff.total_seconds() < 109900


def test_delete_old_jobs_repository_method_range_and_truncate(mocker) -> None:
    # Arrange
    repo = JobRepository(database_url="postgresql://test_user:test_password@localhost:5432/test_db")
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    mock_context = mocker.MagicMock()
    mock_context.__enter__.return_value = mock_conn
    mocker.patch.object(repo, "_connect", return_value=mock_context)

    # Act - range
    start_dt = datetime(2026, 6, 8, 0, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 6, 8, 12, 0, tzinfo=timezone.utc)
    repo.delete_old_jobs(start_date=start_dt, end_date=end_dt)

    # Assert - range query
    query_str, params = mock_conn.execute.call_args[0]
    assert "DELETE FROM jobs WHERE scraped_at >= %s AND scraped_at <= %s" in query_str
    assert params == (start_dt, end_dt)

    # Reset mock and call truncate
    mock_conn.execute.reset_mock()
    repo.delete_old_jobs(truncate=True)

    # Assert - truncate query
    query_str, params = mock_conn.execute.call_args[0]
    assert "DELETE FROM jobs" in query_str
    assert "WHERE" not in query_str
    assert params == ()


def test_is_blacklisted_title() -> None:
    from services.filters import is_blacklisted_title

    assert is_blacklisted_title("Waiter at hotel") is True
    assert is_blacklisted_title("Senior Electrical Engineer") is True
    assert is_blacklisted_title("Draftsman - MEP") is True
    assert is_blacklisted_title("Real Estate Sales Executive") is True
    assert is_blacklisted_title("Civil Construction Manager") is True

    assert is_blacklisted_title("Senior Software Engineer") is False
    assert is_blacklisted_title("Full Stack Developer") is False
    assert is_blacklisted_title("SRE (Site Reliability Engineer)") is False
    assert is_blacklisted_title("System Administrator") is False


def test_save_job_filters_non_software(mocker) -> None:
    repo = JobRepository(database_url="postgresql://test_user:test_password@localhost:5432/test_db")

    # Arrange: We don't expect it to connect or call the DB because it gets filtered first
    mock_connect = mocker.MagicMock()
    mocker.patch.object(repo, "_connect", return_value=mock_connect)

    job = {
        "title": "Professional Waiter",
        "company": "Hotel",
        "url": "https://example.com/waiter-job"
    }

    # Act
    was_saved, fingerprint = repo.save_job(job, source="test")

    # Assert
    assert was_saved is False
    assert fingerprint == repo.fingerprint(job, source="test")
    mock_connect.assert_not_called()

