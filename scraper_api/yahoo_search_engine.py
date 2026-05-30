"""Yahoo search engine implementation."""

import logging
import random
import re
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)


class YahooSearchEngine:
    """Yahoo search engine used for fallback search results."""

    def __init__(self, proxies: Optional[list[str]] = None):
        self.proxies = proxies or []

    def search(self, query: str, max_results: int) -> list[dict]:
        clean_query = re.sub(r"\bafter:\S+", "", query).strip()
        url = "https://search.yahoo.com/search"
        params = {"p": clean_query, "btf": "w"}
        if params["btf"] != "w":
            raise ValueError("Yahoo parameters must strictly contain 'btf' set to 'w'")

        logger.info(f"Yahoo Search: Scraping '{clean_query[:50]}...' via direct connection...")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            with httpx.Client(timeout=8, headers=headers) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    return self._extract_results(resp.text, max_results)
                logger.warning(
                    f"Yahoo Search direct connection returned HTTP {resp.status_code}. Retrying with proxy..."
                )
        except Exception as direct_err:
            logger.warning(f"Yahoo Search direct connection failed: {direct_err}. Retrying with proxy...")

        proxy = random.choice(self.proxies) if self.proxies else None
        proxy_url = proxy if proxy else None
        proxy_name = proxy.split("@")[-1] if proxy else "Direct"
        logger.info(f"Yahoo Search: Scraping '{clean_query[:50]}...' via proxy {proxy_name}...")

        try:
            import httpx

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            client_kwargs = {"timeout": 12, "headers": headers}
            if proxy_url:
                client_kwargs["proxy"] = proxy_url

            with httpx.Client(**client_kwargs) as client:
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        f"Yahoo Search HTTP error status {resp.status_code} for proxy {proxy_name}"
                    )
                    return []
                return self._extract_results(resp.text, max_results)
        except Exception as e:
            logger.error(f"Yahoo Search failed completely: {e}")
            return []

    def _extract_results(self, html: str, max_results: int) -> list[dict]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        containers = soup.find_all("div", class_="algo")
        results = []

        for container in containers:
            if len(results) >= max_results:
                break

            h3 = container.find("h3")
            a_tag = container.find("a")
            snippet_tag = container.find("div", class_="compText") or container.find("span", class_="fc-t")
            if not (h3 and a_tag):
                continue

            title = h3.get_text(strip=True)
            href = a_tag.get("href")
            match = re.search(r"/RU=([^/]+)", href or "")
            if match:
                href = urllib.parse.unquote(match.group(1))
            body = snippet_tag.get_text(strip=True) if snippet_tag else ""
            if href and href.startswith("http") and "yahoo.com" not in href:
                results.append({"title": title, "href": href, "body": body})

        logger.info(f"Yahoo Search successfully extracted {len(results)} results.")
        return results


__all__ = ["YahooSearchEngine"]
