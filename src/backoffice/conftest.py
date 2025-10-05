"""
Conftest for tests located in src/backoffice/features/.

This file makes integration test fixtures from tests/conftest.py available
to tests in the features directory structure.

Pytest only searches upward from the test location, so tests in src/ won't
find fixtures defined in tests/ without this bridge.
"""

import sys
from pathlib import Path

from tests.conftest import (  # noqa: F401
    postgres_container,
    pytest_collection_modifyitems,
    test_client,
    test_db_session,
    test_engine,
)

# Add tests directory to path to enable imports
root_dir = Path(__file__).parent.parent.parent
tests_dir = root_dir / "tests"
sys.path.insert(0, str(tests_dir.parent))
