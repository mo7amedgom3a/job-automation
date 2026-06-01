#!/usr/bin/env python3
"""Use Case: Fetch Software Engineering jobs from Indeed Egypt (Cairo)."""

import os
from utils import run_usecase

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("indeed_eg", "results_indeed_eg.csv")
