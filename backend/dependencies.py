"""FastAPI dependency providers."""

from __future__ import annotations

from cache.cache import DeduplicationCache
from dork_builder import DorkQueryBuilder
from google_api_search_engine import GoogleApiSearcher
from parser import JobResultParser
from repository.jobs import JobRepository
from services.google_search import GoogleJobSearchService
from services.orchestrator import JobOrchestrator
from services.spider_runner import SpiderRunner

_dork_builder = DorkQueryBuilder()
_parser = JobResultParser()
_cache = DeduplicationCache()
_google_searcher = GoogleApiSearcher()
_repository = JobRepository()


def get_dork_builder() -> DorkQueryBuilder:
    return _dork_builder


def get_parser() -> JobResultParser:
    return _parser


def get_cache() -> DeduplicationCache:
    return _cache


def get_google_searcher() -> GoogleApiSearcher:
    return _google_searcher


def get_job_repository() -> JobRepository:
    return _repository


def get_google_job_search_service() -> GoogleJobSearchService:
    return GoogleJobSearchService(
        dork_builder=_dork_builder,
        google_searcher=_google_searcher,
        parser=_parser,
        cache=_cache,
    )


def get_spider_runner() -> SpiderRunner:
    return SpiderRunner(repository=_repository)


def get_orchestrator() -> JobOrchestrator:
    return JobOrchestrator(
        spider_runner=get_spider_runner(),
        google_search_service=get_google_job_search_service(),
    )
