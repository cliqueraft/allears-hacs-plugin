"""Root conftest — adds repo root to sys.path for HA test runner."""
from __future__ import annotations

import pathlib
import sys
import threading

sys.path.insert(0, str(pathlib.Path(__file__).parent))

# The pytest-homeassistant-custom-component verifies no threads linger using threading.enumerate()
# but does *not* provide a fixture to ignore expected ones, causing a race condition error in CI.
# We patch it here to permanently hide the aiohttp safe shutdown thread from the test runner.
_original_enumerate = threading.enumerate


def _filtered_enumerate() -> list[threading.Thread]:
    return [t for t in _original_enumerate() if "_run_safe_shutdown_loop" not in getattr(t, "name", "")]


threading.enumerate = _filtered_enumerate
