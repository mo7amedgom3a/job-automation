#!/usr/bin/env python3
"""Use Case: Fetch remote Software Engineering jobs from LinkedIn Canada."""

import os
from utils import run_usecase

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("linkedin_canada", "results_linkedin_canada.csv")
