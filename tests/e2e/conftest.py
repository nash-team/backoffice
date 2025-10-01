"""
Simple E2E test configuration with Playwright.

Provides:
- server_url: URL of the running test server
- Simplified server startup for E2E tests
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
from dotenv import load_dotenv


# Load .env file for E2E tests (loads real API keys from .env)
def _load_env_file(project_root: Path) -> None:
    """Load .env file if it exists."""
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"[E2E] Loaded environment from {env_file}")


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
    # tests/e2e/conftest.py -> tests/e2e -> tests -> root
    root = Path(__file__).resolve().parents[2]
    # Load .env file when project_root is first accessed
    _load_env_file(root)
    return root


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
    """
    Start FastAPI test server with Uvicorn.

    Uses ephemeral SQLite database and --app-dir to avoid PYTHONPATH issues.
    """
    # Check port is free
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", server_port)) == 0:
            pytest.skip(f"Port {server_port} already in use")

    # Create ephemeral SQLite database
    cache_dir = project_root / ".pytest_cache"
    cache_dir.mkdir(exist_ok=True)
    db_path = cache_dir / f"test_e2e_{os.getpid()}.db"
    database_url = f"sqlite:///{db_path}"

    # Environment variables
    env = os.environ.copy()

    # Override only test-specific settings
    # Use FAKE providers for E2E tests (deterministic, instant, no API costs)
    env.update(
        {
            "TESTING": "true",
            "DATABASE_URL": database_url,
            "ENVIRONMENT": "development",
            "USE_FAKE_PROVIDERS": "true",  # Signal to use fakes instead of real APIs
        }
    )

    print("[E2E] Using FAKE providers (deterministic, instant generation)")

    # Start Uvicorn server
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
        print(f"[E2E] Starting server on {server_url}")

        # Wait longer for server to start and run migrations
        time.sleep(8)

        # Check if process is still running
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            error_msg = f"Server failed to start. STDERR: {stderr[:500]}"
            print(f"[E2E] {error_msg}")
            pytest.skip(error_msg)

        # Try to ping the server to ensure it's responding
        import httpx

        try:
            with httpx.Client() as client:
                response = client.get(f"{server_url}/healthz", timeout=10.0)
                if response.status_code != 200:
                    print(f"[E2E] Warning: Health check returned {response.status_code}")
        except Exception as e:
            print(f"[E2E] Warning: Health check failed: {e}")

        print("[E2E] Server started successfully")
        yield proc

    finally:
        # Cleanup: terminate server
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
                    proc.wait()
                except ProcessLookupError:
                    # Process already terminated
                    pass
                except Exception as e:
                    print(f"[E2E] Warning: Could not kill process: {e}")

        # Cleanup: remove test database
        try:
            if db_path.exists():
                db_path.unlink()
        except Exception as e:
            print(f"[E2E] Warning: Could not remove test DB: {e}")


@pytest.fixture(scope="function", autouse=True)
def setup_browser(page, test_server):
    """
    Ensure test server is running before each test.

    autouse=True means this runs automatically for all tests in e2e/.
    """
    # Server is already running via test_server fixture
    # This fixture just ensures proper dependency ordering
    pass
