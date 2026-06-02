from routes.search import flatten_results


def test_legacy_jobspy_flatten_uses_backend_results() -> None:
    results = {
        "linkedin": [
            {"url": "https://linkedin.com/jobs/view/1", "title": "Backend Engineer"},
            {"url": "https://linkedin.com/jobs/view/1", "title": "Duplicate"},
        ],
        "indeed": [
            {"url": "https://indeed.com/viewjob?jk=2", "title": "Platform Engineer"},
        ],
        "google": [
            {"url": "https://jobs.example.com/3", "title": "Ignored for jobspy route"},
        ],
    }

    flattened = flatten_results(results, max_results=10, sources=["linkedin", "indeed"])

    assert flattened == [
        {"url": "https://linkedin.com/jobs/view/1", "title": "Backend Engineer", "site": "linkedin"},
        {"url": "https://indeed.com/viewjob?jk=2", "title": "Platform Engineer", "site": "indeed"},
    ]


def test_legacy_jobspy_flatten_respects_limit() -> None:
    results = {
        "linkedin": [{"url": "https://linkedin.com/jobs/view/1"}],
        "indeed": [{"url": "https://indeed.com/viewjob?jk=2"}],
        "google": [],
    }

    assert flatten_results(results, max_results=1, sources=["linkedin", "indeed"]) == [
        {"url": "https://linkedin.com/jobs/view/1", "site": "linkedin"}
    ]
