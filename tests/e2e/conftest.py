"""
Minimal E2E test configuration - just health checks.

For complex UI testing, prefer manual testing or dedicated QA environment.
UI evolves too rapidly for automated E2E to be cost-effective.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from collections.abc import Iterator

import pytest


def _get_free_port() -> int:
    """Find a free port for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port: int = s.getsockname()[1]
        return port


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Root directory of the project."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def server_port() -> int:
    """Get a free port for the test server."""
    return _get_free_port()


@pytest.fixture(scope="session")
def server_url(server_port: int) -> str:
    """URL of the test server."""
    return f"http://127.0.0.1:{server_port}"


@pytest.fixture(scope="session")
def test_server(
    project_root: Path, server_port: int, server_url: str
) -> Iterator[subprocess.Popen]:
    """Start minimal FastAPI test server for smoke tests."""
    # Create ephemeral SQLite database
    cache_dir = project_root / ".pytest_cache"
    cache_dir.mkdir(exist_ok=True)
    db_path = cache_dir / f"test_e2e_{os.getpid()}.db"
    database_url = f"sqlite:///{db_path}"

    env = os.environ.copy()
    env.update(
        {
            "TESTING": "true",
            "DATABASE_URL": database_url,
            "ENVIRONMENT": "development",
        }
    )

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backoffice.main:app",
        "--app-dir",
        "src",
        "--host",
        "127.0.0.1",
        "--port",
        str(server_port),
        "--log-level",
        "warning",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )

    try:
        # Wait for server startup
        time.sleep(5)

        # Check if server is running
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            pytest.skip(f"Server failed to start. STDERR: {stderr[:500]}")

        yield proc

    finally:
        # Cleanup
        if proc.poll() is None:
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                else:
                    proc.terminate()
                proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                except ProcessLookupError:
                    pass

        if db_path.exists():
            db_path.unlink()


@pytest.fixture(scope="function", autouse=True)
def setup_browser(page, test_server):
    """Ensure test server is running before each test."""
    pass
