"""Dynamic searcher loader and compatibility exports."""

import importlib
import logging
from typing import Any

logger = logging.getLogger(__name__)

_ENGINE_CLASS_MAP = {
    "duckduckgo": "scraper_api.ddg_search_engine.DuckDuckGoSearcher",
    "ddg": "scraper_api.ddg_search_engine.DuckDuckGoSearcher",
    "yahoo": "scraper_api.yahoo_search_engine.YahooEngine",
    "google_api": "scraper_api.google_api_search_engine.GoogleApiSearcher",
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
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError:
        if module_path.startswith("scraper_api."):
            local_path = module_path.replace("scraper_api.", "", 1)
            try:
                module = importlib.import_module(local_path)
            except ModuleNotFoundError:
                raise
        else:
            raise
            
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
except (ImportError, SystemError) as exc:  # pragma: no cover
    try:
        from ddg_search_engine import DuckDuckGoSearcher
    except ImportError as exc2:
        DuckDuckGoSearcher = None
        logger.warning("Failed to import DuckDuckGoSearcher: %s; fallback failed: %s", exc, exc2)

try:
    from .google_api_search_engine import GoogleApiSearcher
except (ImportError, SystemError) as exc:  # pragma: no cover
    try:
        from google_api_search_engine import GoogleApiSearcher
    except ImportError as exc2:
        GoogleApiSearcher = None
        logger.warning("Failed to import GoogleApiSearcher: %s; fallback failed: %s", exc, exc2)

try:
    from .yahoo_search_engine import YahooSearchEngine
except (ImportError, SystemError) as exc:  # pragma: no cover
    try:
        from yahoo_search_engine import YahooSearchEngine
    except ImportError as exc2:
        YahooSearchEngine = None
        logger.warning("Failed to import YahooSearchEngine: %s; fallback failed: %s", exc, exc2)


__all__ = [
    "Searcher",
    "load_search_engine",
    "DuckDuckGoSearcher",
    "GoogleApiSearcher",
    "YahooSearchEngine",
]
