"""Root conftest — adds repo root to sys.path for HA test runner."""
from __future__ import annotations

import pathlib
import sys
import threading
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))


@pytest.fixture(autouse=True)
def expected_lingering_threads() -> list[str]:
    """Allow aiohttp safe shutdown thread to linger."""
    # This thread is a daemon started by aiohttp to ensure the loop closes.
    # It often lingers for a few ms after client.close() and fails the CI.
    return [t.name for t in threading.enumerate() if "_run_safe_shutdown_loop" in t.name]
