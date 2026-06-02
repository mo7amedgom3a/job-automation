#!/usr/bin/env python3
"""Use Case: Fetch Software Engineering jobs from LinkedIn Egypt (Cairo)."""

import os
from utils import run_usecase

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("linkedin_eg", "results_linkedin_eg.csv")
