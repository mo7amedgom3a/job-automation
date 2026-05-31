"""Example use case for loading live HTTP/HTTPS proxies via ProxyManager."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scraper_api.proxy_manager import ProxyManager


def create_proxy_manager() -> ProxyManager:
    """Instantiate and return a ProxyManager."""
    return ProxyManager()


def get_live_proxies() -> list[str]:
    """Return a list of live HTTP/HTTPS proxies from Geonode."""
    manager = create_proxy_manager()
    return manager.load_dynamic_from_geonode()


if __name__ == "__main__":
    proxies = get_live_proxies()
    print(f"Loaded {len(proxies)} proxies")
    for proxy in proxies[:20]:
        print(proxy)
