"""Filtering helpers shared by routes and orchestration services."""

from __future__ import annotations

import re


BLACKLISTED_COMPANIES = [
    "crossing hurdles",
    "turing",
    "confidential",
    "confidential careers",
    "micro1",
    "canonical",
    "naphora games group",
    "meridial marketplace",
    "by invisible",
    "invisible",
    "siira",
    "proxify",
    "dataannotation",
    "mindrift",
    "mercor",
    "jobgether",
]


def is_blacklisted_company(company_name: str | None) -> bool:
    if not company_name:
        return False
    name_lower = company_name.lower().strip()
    return any(blocked in name_lower for blocked in BLACKLISTED_COMPANIES)


def is_within_24_hours(date_str: str, snippet: str = "") -> bool:
    text_to_check = (date_str or snippet or "").lower()

    if any(k in text_to_check for k in ["hour", "minute", "min", "second", "just now"]):
        match = re.search(r"(\d+)\s+hours?\s+ago", text_to_check)
        if match:
            return int(match.group(1)) <= 24
        return True

    if any(k in text_to_check for k in ["day", "week", "month", "year", "yesterday"]):
        return False

    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    if any(month in text_to_check for month in months):
        return False

    return True
