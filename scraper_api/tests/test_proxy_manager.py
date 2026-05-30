from unittest.mock import MagicMock, patch

from scraper_api.proxy_manager import ProxyManager


def test_format_geonode_proxy_returns_socks5_url() -> None:
    proxy_data = {
        "ip": "1.2.3.4",
        "port": "1080",
        "protocols": ["socks5"],
    }

    formatted = ProxyManager.format_geonode_proxy(proxy_data)

    assert formatted == "socks5://1.2.3.4:1080"


def test_load_dynamic_from_geonode_parses_response() -> None:
    response_data = {
        "data": [
            {
                "ip": "1.2.3.4",
                "port": "1080",
                "protocols": ["socks5"],
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 1,
    }

    response_mock = MagicMock()
    response_mock.raise_for_status.return_value = None
    response_mock.json.return_value = response_data

    client_mock = MagicMock()
    client_mock.get.return_value = response_mock

    client_context = MagicMock()
    client_context.__enter__.return_value = client_mock
    client_context.__exit__.return_value = None

    with patch("scraper_api.proxy_manager.httpx.Client", return_value=client_context):
        proxy_manager = ProxyManager(proxies=[])
        proxies = proxy_manager.load_dynamic_from_geonode(page=1, limit=1)

    assert proxies == ["socks5://1.2.3.4:1080"]
    assert len(proxy_manager) == 1
