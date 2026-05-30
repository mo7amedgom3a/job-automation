"""Proxy loading and management for the scraper_api package."""

from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Iterable, List, Optional

from scraper_api.utils.webshare_proxies import fetch_all_proxies, get_api_token

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROXY_FILE = ROOT.parent / "Webshare-proxies.txt"


class ProxyManager:
    """Encapsulates proxy source loading and selection for searchers."""

    def __init__(
        self,
        proxies: Optional[Iterable[str]] = None,
        proxy_file: Optional[str] = None,
    ) -> None:
        self.proxy_file = Path(proxy_file) if proxy_file else DEFAULT_PROXY_FILE
        self.proxies: List[str] = list(proxies) if proxies is not None else self.load_from_file(self.proxy_file)

    def load_from_file(self, proxy_file: Path | str) -> List[str]:
        path = Path(proxy_file)
        if not path.exists():
            return []

        proxies: List[str] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            proxy_url = self.format_proxy_line(line)
            if proxy_url:
                proxies.append(proxy_url)
        return proxies

    def refresh_from_file(self) -> List[str]:
        self.proxies = self.load_from_file(self.proxy_file)
        return self.proxies

    def load_dynamic_from_webshare(
        self,
        api_key: Optional[str] = None,
        mode: str = "direct",
        page_size: int = 100,
        country_code__in: Optional[str] = None,
        search: Optional[str] = None,
        ordering: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> List[str]:
        api_key = api_key or get_api_token()
        raw_proxies = fetch_all_proxies(
            api_key=api_key,
            mode=mode,
            page_size=page_size,
            country_code__in=country_code__in,
            search=search,
            ordering=ordering,
            plan_id=plan_id,
        )
        self.proxies = [p for p in map(self.format_proxy_line, raw_proxies) if p]
        return self.proxies

    @staticmethod
    def format_proxy_line(line: str) -> Optional[str]:
        parts = line.strip().split(":")
        if len(parts) != 4:
            return None
        ip, port, username, password = parts
        return f"http://{username}:{password}@{ip}:{port}"

    def get_random_proxies(self, count: int = 3) -> List[str]:
        if not self.proxies:
            return []
        count = min(count, len(self.proxies))
        return random.sample(self.proxies, count)

    def __len__(self) -> int:
        return len(self.proxies)
