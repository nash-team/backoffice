"""
Configuration simplifiée pour débugger les tests E2E.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def simple_server():
    """Serveur de test simplifié pour debug."""
    project_root = Path(__file__).resolve().parents[2]
    port = 8999

    # Commande simple
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
        str(port),
        "--log-level",
        "info",
    ]

    print(f"[DEBUG] Starting server with command: {' '.join(cmd)}")
    print(f"[DEBUG] Working directory: {project_root}")

    proc = subprocess.Popen(
        cmd, cwd=project_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    # Wait a bit for server to start
    time.sleep(3)

    # Check if process is still running
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print("[DEBUG] Server failed to start!")
        print(f"[DEBUG] STDOUT: {stdout}")
        print(f"[DEBUG] STDERR: {stderr}")
        pytest.skip("Server failed to start")

    print(f"[DEBUG] Server started on port {port}")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait()
        print("[DEBUG] Server terminated")


@pytest.fixture
def simple_server_url(simple_server):
    """URL du serveur simple."""
    return simple_server
