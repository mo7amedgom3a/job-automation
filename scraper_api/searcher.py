"""Dynamic searcher loader and compatibility exports."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_ENGINE_CLASS_MAP = {
    "duckduckgo": "scraper_api.ddg_search_engine.DuckDuckGoSearcher",
    "ddg": "scraper_api.ddg_search_engine.DuckDuckGoSearcher",
    "yahoo": "scraper_api.yahoo_search_engine.YahooSearchEngine",
    "jobspy": "scraper_api.jobspy_search_engine.JobSpySearcher",
    "python-jobspy": "scraper_api.jobspy_search_engine.JobSpySearcher",
}


def load_search_engine(engine_name: str) -> Any:
    if not engine_name or not engine_name.strip():
        raise ValueError("engine_name must be a non-empty string")

    key = engine_name.strip().lower()
    if key not in _ENGINE_CLASS_MAP:
        raise ValueError(
            f"Unsupported search engine '{engine_name}'. Supported engines: {sorted(set(_ENGINE_CLASS_MAP.keys()))}"
        )

    module_path, class_name = _ENGINE_CLASS_MAP[key].rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class Searcher:
    """Loader wrapper for dynamically instantiating a search engine."""

    def __init__(self, engine_name: str, **kwargs: Any) -> None:
        engine_cls = load_search_engine(engine_name)
        logger.info(f"Initializing search engine '{engine_name}' -> {engine_cls.__name__}")
        self.engine = engine_cls(**kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.engine, name)


try:
    from .ddg_search_engine import DuckDuckGoSearcher
    from .jobspy_search_engine import JobSpySearcher
    from .yahoo_search_engine import YahooSearchEngine
except ImportError:  # pragma: no cover
    DuckDuckGoSearcher = None
    JobSpySearcher = None
    YahooSearchEngine = None


__all__ = [
    "Searcher",
    "load_search_engine",
    "DuckDuckGoSearcher",
    "JobSpySearcher",
    "YahooSearchEngine",
]
