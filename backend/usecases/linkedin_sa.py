#!/usr/bin/env python3
"""Use Case: Fetch remote Software Engineering jobs from LinkedIn Saudi Arabia."""

import os
from utils import run_usecase

if __name__ == "__main__":
    # Ensure current working directory is the script's folder so local imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_usecase("linkedin_sa", "results_linkedin_sa.csv")
