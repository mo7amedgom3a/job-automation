#!/usr/bin/env python3
"""Use Case: Fetch remote Software Engineering jobs from LinkedIn Spain."""

import os
from utils import run_usecase

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("linkedin_spain", "results_linkedin_spain.csv")
