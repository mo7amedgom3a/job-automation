#!/usr/bin/env python3
"""
Scraper Engine Entry Point
===========================
Executes the scraping cycle scheduler from the root directory.

Usage:
  python3 run.py --once --site indeed
  python3 run.py --once --site linkedin_eg
  python3 run.py --interval 2
"""

import os
import sys
from pathlib import Path

# Add package directory to Python path
sys.path.insert(0, str(Path(__file__).parent.absolute() / "job_scraper_engine"))

# Ensure we use a single consistent absolute SQLite DB path inside the package folder
os.environ["SQLITE_DB_PATH"] = str(Path(__file__).parent.absolute() / "job_scraper_engine" / "jobs.db")

from scheduler.runner import main

if __name__ == "__main__":
    main()
