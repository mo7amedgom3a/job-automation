"""Google Search API Engine (Serper.dev / SerpApi) implementation."""

import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


class GoogleApiSearcher:
    """
    Searcher that uses standard Google search APIs (Serper.dev or SerpApi) 
    to retrieve highly precise, real-time Google search results.
    """

    def __init__(self, timeout: int = 15, **kwargs):
        self.timeout = timeout
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")

        if self.serper_api_key:
            logger.info("GoogleApiSearcher: Serper.dev API key loaded.")
        if self.serpapi_api_key:
            logger.info("GoogleApiSearcher: SerpApi API key loaded.")
        if not self.serper_api_key and not self.serpapi_api_key:
            logger.warning("GoogleApiSearcher: Neither SERPER_API_KEY nor SERPAPI_API_KEY is configured!")

    async def search(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Executes a Google Search query using Serper.dev as primary and SerpApi as fallback.
        """
        if self.serper_api_key:
            try:
                return await self._search_serper(query, max_results)
            except Exception as e:
                logger.error(f"GoogleApiSearcher: Serper.dev query failed: {e}. Trying fallback SerpApi...")

        if self.serpapi_api_key:
            try:
                return await self._search_serpapi(query, max_results)
            except Exception as e:
                logger.error(f"GoogleApiSearcher: SerpApi query failed: {e}")

        logger.error("GoogleApiSearcher: All Google API search engines failed or keys are missing.")
        return []

    async def _search_serper(self, query: str, max_results: int) -> list[dict]:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": max_results,
            "tbs": "qdr:d"  # Past 24 hours filter
        }

        logger.info(f"GoogleApiSearcher [Serper]: Querying Google for '{query[:60]}...'")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

            results = []
            organic = data.get("organic", [])
            for item in organic:
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                date_str = item.get("date", "")

                results.append({
                    "title": title,
                    "href": link,
                    "body": snippet,
                    "date": date_str
                })
            logger.info(f"GoogleApiSearcher [Serper]: Retrieved {len(results)} organic results.")
            return results

    async def _search_serpapi(self, query: str, max_results: int) -> list[dict]:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.serpapi_api_key,
            "num": max_results,
            "tbs": "qdr:d"  # Past 24 hours filter
        }

        logger.info(f"GoogleApiSearcher [SerpApi]: Querying Google for '{query[:60]}...'")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            results = []
            organic = data.get("organic_results", [])
            for item in organic:
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                date_str = item.get("date", "")

                results.append({
                    "title": title,
                    "href": link,
                    "body": snippet,
                    "date": date_str
                })
            logger.info(f"GoogleApiSearcher [SerpApi]: Retrieved {len(results)} organic results.")
            return results
