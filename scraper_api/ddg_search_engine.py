"""DuckDuckGo search engine implementation."""

import asyncio
import logging
import random
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class DuckDuckGoSearcher:
    """DuckDuckGo searcher with optional proxy rotation and Yahoo fallback."""

    def __init__(
        self,
        max_concurrent: int = 3,
        delay_between: float = 1.5,
        timeout: int = 35,
        max_retries: int = 2,
        proxies: Optional[list[str]] = None,
        proxy_manager: Optional["ProxyManager"] = None,
    ):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.delay_between = delay_between
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request = 0.0
        self.lock = asyncio.Lock()
        self.proxy_manager = proxy_manager
        self.proxies = (
            proxies
            if proxies is not None
            else proxy_manager.proxies
            if proxy_manager is not None
            else []
        )
        if self.proxies:
            logger.info(f"DuckDuckGoSearcher: Loaded {len(self.proxies)} proxies.")
        else:
            logger.info("DuckDuckGoSearcher: No proxies loaded, using direct connection.")

    async def search_all(
        self,
        queries: list[dict],
        max_per_query: int = 20,
        timelimit: str = "d",
    ) -> list[dict]:
        tasks = [
            self._search_one(q, max_per_query, timelimit)
            for q in queries
        ]
        results_nested = await asyncio.gather(*tasks, return_exceptions=True)

        flat = []
        for q, res in zip(queries, results_nested):
            if isinstance(res, Exception):
                logger.warning(f"Query failed [{q.get('strategy')}]: {q.get('query', '')[:60]} — {res}")
                continue
            for r in res:
                r["_dork_query"] = q.get("query", "")
                r["_dork_keyword"] = q.get("keyword", "")
                r["_dork_site"] = q.get("site", "")
                r["_dork_strategy"] = q.get("strategy", "")
            flat.extend(res)

        logger.info(f"search_all: {len(queries)} queries → {len(flat)} raw results")
        return flat

    async def _search_one(
        self,
        query_dict: dict,
        max_results: int,
        timelimit: str,
    ) -> list[dict]:
        query = query_dict["query"]

        for attempt in range(self.max_retries + 1):
            try:
                async with self.semaphore:
                    async with self.lock:
                        now = time.time()
                        since_last = now - self._last_request
                        if since_last < self.delay_between:
                            await asyncio.sleep(self.delay_between - since_last)
                        self._last_request = time.time()

                    results = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda q=query, n=max_results, t=timelimit: self._ddg_search(q, n, t),
                        ),
                        timeout=self.timeout,
                    )
                    return results

            except asyncio.TimeoutError:
                logger.warning(f"Timeout on query (attempt {attempt+1}): {query[:60]}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                err_str = str(e).lower()
                if "ratelimit" in err_str or "202" in err_str:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"Rate limited — waiting {wait}s before retry")
                    await asyncio.sleep(wait)
                else:
                    raise

        return []

    def _ddg_search(self, query: str, max_results: int, timelimit: str) -> list[dict]:
        from duckduckgo_search import DDGS

        clean_query = re.sub(r"\bafter:\S+", "", query).strip()
        today = datetime.now()
        three_days_ago = today - timedelta(days=3)
        df_val = f"{three_days_ago.strftime('%Y-%m-%d')}..{today.strftime('%Y-%m-%d')}" 

        if self.proxy_manager is not None:
            shuffled_proxies = self.proxy_manager.get_random_proxies(3)
        else:
            shuffled_proxies = list(self.proxies)
            random.shuffle(shuffled_proxies)
            shuffled_proxies = shuffled_proxies[:3]

        if not shuffled_proxies:
            shuffled_proxies = [None]

        logger.info(
            f"DDGS Search: Searching '{clean_query[:50]}...' using sequential proxy rotation across {len(shuffled_proxies)} proxies with curl_cffi."
        )

        for idx, proxy in enumerate(shuffled_proxies):
            proxy_url = proxy if proxy else None
            proxy_name = proxy.split("@")[-1] if proxy else "Direct"

            logger.info(f"DDGS Search (Proxy {idx+1}/{len(shuffled_proxies)}): Trying {proxy_name}...")

            try:
                time.sleep(random.uniform(1.0, 2.0))
                with DDGS(proxy=proxy_url, timeout=8) as ddgs:
                    raw_results = list(
                        ddgs.text(
                            clean_query,
                            max_results=max_results,
                            timelimit=df_val,
                            backend="lite",
                        )
                    )

                    results = []
                    for r in raw_results:
                        title = r.get("title", "")
                        href = r.get("href", "")
                        body = r.get("body", "")

                        if href and href.startswith("http") and "duckduckgo.com" not in href:
                            results.append({"title": title, "href": href, "body": body})

                    logger.info(
                        f"DDGS Search successfully extracted {len(results)} results via proxy {proxy_name}."
                    )
                    return results

            except Exception as e:
                logger.warning(f"DDGS Search proxy {proxy_name} error: {e}. Trying next proxy...")
                continue

        logger.error(
            f"DDGS Search failed completely: all {len(shuffled_proxies)} proxies were exhausted or blocked."
        )

        logger.warning(
            "All DuckDuckGo proxies exhausted or challenge-blocked. Initiating Yahoo Search fallback..."
        )
        try:
            from scraper_api.yahoo_search_engine import YahooSearchEngine

            yahoo = YahooSearchEngine(proxies=self.proxies)
            return yahoo.search(query, max_results)
        except Exception as yahoo_err:
            logger.error(f"Yahoo Search fallback failed: {yahoo_err}")
            return []


__all__ = ["DuckDuckGoSearcher"]
