#!/usr/bin/env python3
"""Use Case: Fetch remote Software Engineering jobs from Indeed Germany."""

import os
from utils import run_usecase

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("indeed_germany", "results_indeed_germany.csv")
