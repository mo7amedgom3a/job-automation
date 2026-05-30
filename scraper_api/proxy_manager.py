"""Proxy loading and management for the scraper_api package."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Iterable, List, Optional

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROXY_FILE = ROOT.parent / "Webshare-proxies.txt"
GEONODE_PROXY_LIST_URL = "https://proxylist.geonode.com/api/proxy-list"


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

    def load_dynamic_from_geonode(
        self,
        protocols: str = "socks5",
        filter_last_checked: int = 1,
        speed: str = "fast",
        page: int = 1,
        limit: int = 500,
        sort_by: str = "speed",
        sort_type: str = "asc",
    ) -> List[str]:
        params = {
            "protocols": protocols,
            "filterLastChecked": filter_last_checked,
            "speed": speed,
            "page": page,
            "limit": limit,
            "sort_by": sort_by,
            "sort_type": sort_type,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(GEONODE_PROXY_LIST_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError):
            return []

        raw_proxies = payload.get("data", []) if isinstance(payload, dict) else []
        self.proxies = [p for p in map(self.format_geonode_proxy, raw_proxies) if p]
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
        """Legacy alias kept for compatibility; now uses Geonode-based proxy discovery."""
        return self.load_dynamic_from_geonode()

    @staticmethod
    def format_geonode_proxy(proxy: dict[str, Any]) -> Optional[str]:
        ip = proxy.get("ip")
        port = proxy.get("port")
        protocols = proxy.get("protocols") or []
        if not ip or not port or not protocols:
            return None

        protocol = protocols[0]
        if protocol not in {"http", "https", "socks4", "socks5"}:
            return None

        return f"{protocol}://{ip}:{port}"

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
