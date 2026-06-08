"""FastAPI application factory for the job aggregation backend."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv()

from dependencies import get_job_repository
from routes.cache import router as cache_router
from routes.health import router as health_router
from routes.jobs import router as jobs_router
from routes.queries import router as queries_router
from routes.search import router as search_router

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Job Board Scraping & Aggregation Engine",
        description=(
            "A unified high-performance job board scraping and aggregation API. "
            "Integrates parallel Playwright scrapers (LinkedIn, Indeed) and Google API Search dorks. "
            "Includes 1-hour database cache caching, URL deduplication, custom query dorking, "
            "and health indicators."
        ),
        version="4.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(search_router)
    app.include_router(queries_router)
    app.include_router(cache_router)
    app.include_router(jobs_router)

    @app.on_event("startup")
    async def startup() -> None:
        get_job_repository().init_schema()

    return app


app = create_app()
