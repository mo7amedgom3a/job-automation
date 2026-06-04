import pytest
from datetime import datetime, timezone, timedelta
from typing import Any

from services.filters import is_within_3_days
from spiders.base import BaseJobSpider
from config.settings import SiteConfig


def test_is_within_3_days_relative() -> None:
    # 1. Relative checks (should keep)
    assert is_within_3_days("3 hours ago") is True
    assert is_within_3_days("yesterday") is True
    assert is_within_3_days("2d") is True
    assert is_within_3_days("3 days ago") is True
    assert is_within_3_days("1 minute ago") is True
    assert is_within_3_days("today") is True
    assert is_within_3_days(None) is True  # fail-safe

    # 2. Relative checks (should discard)
    assert is_within_3_days("4 days ago") is False
    assert is_within_3_days("4d") is False
    assert is_within_3_days("2 weeks ago") is False
    assert is_within_3_days("1 month ago") is False
    assert is_within_3_days("1 year ago") is False


def test_is_within_3_days_absolute() -> None:
    now = datetime.now(timezone.utc)
    
    # Within 3 days (e.g. 1.5 days ago)
    date_ok = (now - timedelta(days=1, hours=12)).isoformat()
    assert is_within_3_days(date_ok) is True

    # Older than 3 days (e.g. 4 days ago)
    date_old = (now - timedelta(days=4)).isoformat()
    assert is_within_3_days(date_old) is False

    # Timestamp within 3 days
    ts_ok = str((now - timedelta(days=2)).timestamp())
    assert is_within_3_days(ts_ok) is True

    # Timestamp older than 3 days
    ts_old = str((now - timedelta(days=5)).timestamp())
    assert is_within_3_days(ts_old) is False


@pytest.mark.asyncio
async def test_base_spider_drops_old_remote_jobs(mocker: Any) -> None:
    # Setup mock site configs
    remote_cfg = SiteConfig(name="remoteok", start_urls=["http://example.com"])
    non_remote_cfg = SiteConfig(name="linkedin", start_urls=["http://example.com"])

    # Mock save_job database call
    mock_save = mocker.patch("spiders.base.save_job", return_value=(True, "fingerprint_123"))

    # 1. Test RemoteOK spider (should drop old jobs)
    class DummyRemoteSpider(BaseJobSpider):
        site_config = remote_cfg
        async def extract_jobs(self, response: Any):
            yield {}

    spider_remote = DummyRemoteSpider()
    spider_remote._run_id = 1
    spider_remote._items_new = 0
    spider_remote._items_dupe = 0
    spider_remote.logger = mocker.MagicMock()

    # Case A: Job posted 2 days ago (should NOT be dropped, i.e. returns the item)
    job_new = {"title": "Python Dev", "url": "http://ok.com/1", "date_posted": "2 days ago"}
    res_new = await spider_remote.on_scraped_item(job_new)
    assert res_new is not None
    assert mock_save.call_count == 1

    # Case B: Job posted 5 days ago (should be dropped, i.e. returns None)
    mock_save.reset_mock()
    job_old = {"title": "Go Dev", "url": "http://ok.com/2", "date_posted": "5 days ago"}
    res_old = await spider_remote.on_scraped_item(job_old)
    assert res_old is None
    assert mock_save.call_count == 0

    # Case C: Job with missing date (should NOT be dropped as a fail-safe, i.e. returns the item)
    mock_save.reset_mock()
    job_missing = {"title": "React Dev", "url": "http://ok.com/3"}
    res_missing = await spider_remote.on_scraped_item(job_missing)
    assert res_missing is not None
    assert mock_save.call_count == 1

    # 2. Test LinkedIn spider (should NOT drop old jobs)
    class DummyLinkedInSpider(BaseJobSpider):
        site_config = non_remote_cfg
        async def extract_jobs(self, response: Any):
            yield {}

    spider_linkedin = DummyLinkedInSpider()
    spider_linkedin._run_id = 2
    spider_linkedin._items_new = 0
    spider_linkedin._items_dupe = 0
    spider_linkedin.logger = mocker.MagicMock()

    mock_save.reset_mock()
    job_linkedin_old = {"title": "Staff Engineer", "url": "http://li.com/1", "date_posted": "2 weeks ago"}
    res_li = await spider_linkedin.on_scraped_item(job_linkedin_old)
    assert res_li is not None
    assert mock_save.call_count == 1
