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
    "jobright.ai",
    "hire feed",
    "Hire Feed", 
    "revolut",
    "hired",
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


def is_within_3_days(date_str: str | None) -> bool:
    if not date_str:
        return True  # fail-safe: keep if date is missing

    text = date_str.lower().strip()

    # 1. Relative checks (hours/minutes/seconds/today/just now/yesterday)
    if any(k in text for k in ["hour", "minute", "min", "second", "just now", "today"]):
        return True
    if "yesterday" in text:
        return True

    # 2. Check "X days ago" or "Xd" patterns
    import re
    match_days = re.search(r"(\d+)\s*d(ay)?s?\s*(ago)?", text)
    if match_days:
        return int(match_days.group(1)) <= 3

    # 3. Check weeks/months/years
    if any(k in text for k in ["week", "month", "year", "w", "mo", "yr"]):
        return False

    # 4. Try parsing as ISO format / absolute timestamp
    from datetime import datetime, timezone, timedelta
    try:
        clean_text = text.replace(" ", "T")
        if "t" in clean_text:
            dt = datetime.fromisoformat(clean_text)
        else:
            dt = datetime.strptime(text, "%Y-%m-%d")
        
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        now = datetime.now(timezone.utc)
        return now - dt <= timedelta(days=3)
    except Exception:
        pass

    # 5. Try parsing month names (e.g. "May 31", "Jun 2")
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    for month_abbr, month_num in months.items():
        if month_abbr in text:
            match_num = re.search(r"\b(\d{1,2})\b", text)
            if match_num:
                day = int(match_num.group(1))
                now = datetime.now(timezone.utc)
                year = now.year
                try:
                    dt = datetime(year, month_num, day, tzinfo=timezone.utc)
                    if dt > now:
                        dt = dt.replace(year=year - 1)
                    return now - dt <= timedelta(days=3)
                except ValueError:
                    pass

    # 6. Try raw timestamp integer
    try:
        ts = float(text)
        dt = datetime.fromtimestamp(ts, timezone.utc)
        now = datetime.now(timezone.utc)
        return now - dt <= timedelta(days=3)
    except ValueError:
        pass

    return True


def is_blacklisted_title(title: str | None) -> bool:
    """Checks if a job title is not related to the software field (e.g. Waiter, Electrical, Sales)."""
    if not title:
        return False
    title_lower = title.lower().strip()

    patterns = [
        # Explicit user list
        r"\bwaiter\b", r"\bwaitress\b",
        r"\belectrical\b", r"\belectrician\b",
        r"\bdraftsman\b", r"\bdraftsmen\b",
        r"\bdraftsperson\b",
        r"\baluminium\b", r"\baluminum\b",
        r"\bdrainage\b",
        r"\bmarketing\b",
        r"\breal\s*estate\b",
        r"\bproperty\b",
        r"\bmetal\b",
        r"\blight\b",
        r"\bmaterials\b",
        r"\bconstruction\b",
        r"\bmep\b",
        r"\bland\b",
        r"\bland\s+sales\b",
        r"\bsales\b",
        r"\bcivil\b",
        

        # Common construction/non-software leaks
        r"\bplumbing\b", r"\bplumber\b",
        r"\bpiping\b",
        r"\bhvac\b",
        r"\bmechanical\b",
        r"\bquantity\s+surveyor\b",
        r"\bdriver\b", r"\bstorekeeper\b", r"\bwarehouse\b",
        r"\baccountant\b", r"\baccounting\b",
        r"\bhr\b", r"\bhuman\s+resources\b",
        r"\bnurse\b", r"\bdoctor\b", r"\bpharmacist\b",
        r"\bchef\b", r"\bcook\b",
    ]

    for pattern in patterns:
        if re.search(pattern, title_lower):
            return True

    return False

