"""Fetch Webshare proxies and dump them into Webshare-proxies.txt.

This script reads the API token from the local .env file or from the
WEBSHARE_KEY environment variable, calls Webshare's proxy list endpoint,
and stores proxies in the format used by this project:

    ip:port:username:password

By default it fetches direct proxies and follows pagination.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOTENV = ROOT / ".env"
DEFAULT_OUTPUT = ROOT / "Webshare-proxies.txt"
API_BASE = "https://proxy.webshare.io/api/v2/proxy/list/"


def load_env_file(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not env_path.exists():
        return env

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def get_api_token(env_path: Path | None = None) -> str:
    if api_key := os.getenv("WEBSHARE_KEY"):
        return api_key

    env_path = env_path or DEFAULT_DOTENV
    env = load_env_file(env_path)
    if api_key := env.get("WEBSHARE_KEY"):
        return api_key

    raise RuntimeError(
        f"WEBSHARE_KEY not found in environment or {env_path}."
    )


def fetch_proxy_page(
    api_key: str,
    mode: str,
    page: int,
    page_size: int,
    country_code__in: str | None = None,
    search: str | None = None,
    ordering: str | None = None,
    created_at: str | None = None,
    proxy_address: str | None = None,
    proxy_address__in: str | None = None,
    valid: bool | None = None,
    asn_number: str | None = None,
    asn_name: str | None = None,
    plan_id: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "mode": mode,
        "page": page,
        "page_size": page_size,
    }

    if country_code__in:
        params["country_code__in"] = country_code__in
    if search:
        params["search"] = search
    if ordering:
        params["ordering"] = ordering
    if created_at:
        params["created_at"] = created_at
    if proxy_address:
        params["proxy_address"] = proxy_address
    if proxy_address__in:
        params["proxy_address__in"] = proxy_address__in
    if valid is not None:
        params["valid"] = str(valid).lower()
    if asn_number:
        params["asn_number"] = asn_number
    if asn_name:
        params["asn_name"] = asn_name
    if plan_id:
        params["plan_id"] = plan_id

    response = requests.get(
        API_BASE,
        params=params,
        headers={"Authorization": f"Token {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def format_proxy(item: dict[str, Any]) -> str | None:
    address = item.get("proxy_address")
    port = item.get("port")
    username = item.get("username")
    password = item.get("password")
    if not all([address, port, username, password]):
        return None
    return f"{address}:{port}:{username}:{password}"


def fetch_all_proxies(
    api_key: str,
    mode: str,
    page_size: int,
    country_code__in: str | None,
    search: str | None,
    ordering: str | None,
    plan_id: str | None,
) -> list[str]:
    proxies: list[str] = []
    page = 1

    while True:
        payload = fetch_proxy_page(
            api_key=api_key,
            mode=mode,
            page=page,
            page_size=page_size,
            country_code__in=country_code__in,
            search=search,
            ordering=ordering,
            plan_id=plan_id,
        )

        results = payload.get("results", [])
        if not results:
            break

        for item in results:
            line = format_proxy(item)
            if line:
                proxies.append(line)

        if not payload.get("next"):
            break

        page += 1

    return proxies


def save_proxies(proxies: list[str], output_path: Path) -> None:
    output_path.write_text("\n".join(proxies) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch Webshare proxies and write them to Webshare-proxies.txt."
    )
    parser.add_argument(
        "--mode",
        default="direct",
        choices=["direct", "backbone"],
        help="Webshare proxy mode, required by the API. Use direct by default.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="Number of proxies to request per API page.",
    )
    parser.add_argument(
        "--country-codes",
        default=None,
        help="Comma-separated country codes to filter, e.g. US,FR.",
    )
    parser.add_argument(
        "--search",
        default=None,
        help="Search phrase filter for proxy metadata.",
    )
    parser.add_argument(
        "--ordering",
        default=None,
        help="Ordering string for the proxy list.",
    )
    parser.add_argument(
        "--plan-id",
        default=None,
        help="Optional Webshare plan ID to target a specific plan.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output file path for saved proxies.",
    )
    parser.add_argument(
        "--env-file",
        default=str(DEFAULT_DOTENV),
        help="Path to .env file containing WEBSHARE_KEY.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save to file, only print proxy lines.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    api_key = get_api_token(Path(args.env_file))
    proxies = fetch_all_proxies(
        api_key=api_key,
        mode=args.mode,
        page_size=args.page_size,
        country_code__in=args.country_codes,
        search=args.search,
        ordering=args.ordering,
        plan_id=args.plan_id,
    )

    if not proxies:
        print("No proxies were returned by the Webshare API.")
        return

    print(f"Fetched {len(proxies)} proxies from Webshare.")
    for line in proxies:
        print(line)

    if not args.no_save:
        save_proxies(proxies, Path(args.output))
        print(f"Saved {len(proxies)} proxies to {args.output}")


if __name__ == "__main__":
    main()
