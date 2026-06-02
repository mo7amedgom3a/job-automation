"""Compatibility import for the refactored backend orchestrator.

The implementation now lives in backend.services.orchestrator as part of the
layered backend architecture. This module remains so older imports of
scraper_api.orchestrator.JobOrchestrator continue to work from the repository
root.
"""

from __future__ import annotations

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parents[1] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from services.orchestrator import JobOrchestrator
except ModuleNotFoundError as exc:  # pragma: no cover - compatibility guidance.
    raise ModuleNotFoundError(
        "JobOrchestrator moved to backend.services.orchestrator. "
        "Run from the repository root or use the backend container."
    ) from exc

__all__ = ["JobOrchestrator"]
