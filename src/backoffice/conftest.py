"""
Conftest for tests located in src/backoffice/features/.

This file makes integration test fixtures from tests/conftest.py available
to tests in the features directory structure.

Pytest only searches upward from the test location, so tests in src/ won't
find fixtures defined in tests/ without this bridge.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add tests directory to path to enable imports
root_dir = Path(__file__).parent.parent.parent
tests_dir = root_dir / "tests"
sys.path.insert(0, str(tests_dir.parent))

try:
    from tests.conftest import (  # noqa: F401
        postgres_container,
        pytest_collection_modifyitems,
        test_client,
        test_db_session,
        test_engine,
    )
except ImportError:
    # Integration dependencies (cryptography, testcontainers, etc.) not available.
    # Fixtures will not be registered — integration tests will be skipped.
    from tests.conftest import pytest_collection_modifyitems  # noqa: F401
