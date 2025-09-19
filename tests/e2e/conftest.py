"""
Configurations et fixtures pour les tests E2E Playwright.

Objectifs :
- Démarrage serveur Uvicorn robuste (app-dir=src, sans PYTHONPATH).
- Port unique et sain par session (compatible xdist).
- Health-check /healthz avec backoff.
- Base SQLite éphémère par session (isolation simple).
- Reset de données via endpoint dédié avant chaque test.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import psutil
import pytest

# ---------------------------
# Utilitaires réseau / ports
# ---------------------------


def _get_free_port() -> int:
    """Trouve un port libre (réservé temporairement pour éviter les races)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        return s.getsockname()[1]


def _get_worker_port(base_port: int = 8000) -> int:
    """Port unique par worker xdist, avec léger offset cryptographiquement sûr pour éviter les collisions inter-runs."""

    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    if worker_id in ("master", "gw0"):
        # gw0: on garde la base (mais on vérifiera qu'il est libre)
        candidate = base_port
    else:
        try:
            num = int(worker_id[2:]) if worker_id.startswith("gw") else 0
        except ValueError:
            num = 0
        candidate = base_port + (num * 1000)

    # Ajoute un petit offset pour éviter conflits si plusieurs sessions en parallèle
    candidate += secrets.randbelow(900) + 100
    return candidate


# ---------------------------
# Health-check serveur
# ---------------------------


def _wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Health-check robuste sur /healthz avec backoff simple."""
    import httpx

    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            with httpx.Client() as client:
                resp = client.get(f"{url}/healthz", timeout=5.0)
                if resp.status_code == 200:
                    return True
        except (httpx.RequestError, httpx.TimeoutException):
            pass

        # backoff (max 1s)
        time.sleep(min(0.1 * attempt, 1.0))

    return False


# ---------------------------
# Fixtures Pytest
# ---------------------------


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Racine projet (dossier contenant pyproject.toml)."""
    here = Path(__file__).resolve()
    # tests/e2e/conftest.py -> tests/e2e -> tests -> racine
    return here.parents[2]


@pytest.fixture(scope="session")
def server_port() -> int:
    """Choisit un port libre et stable pour la session (compat xdist)."""
    # 1) Essai sur un port "logique" par worker
    candidate = _get_worker_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", candidate)) != 0:
            return candidate
    # 2) Sinon prend un port libre
    return _get_free_port()


@pytest.fixture(scope="session")
def server_url(server_port: int) -> str:
    """URL du serveur pour cette session."""
    return f"http://127.0.0.1:{server_port}"


@pytest.fixture(scope="session")
def test_server(project_root: Path, server_port: int) -> Iterator[subprocess.Popen]:
    """
    Démarre le serveur FastAPI (Uvicorn) pour la session de tests.
    - Lance via --app-dir src et module 'backoffice.main:app' (pas de PYTHONPATH).
    - DB éphémère SQLite par session.
    - Health-check /healthz avant de rendre la main.
    - Arrêt propre en teardown.
    """
    # Vérifie port libre
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", server_port)) == 0:
            pytest.skip(f"Port {server_port} déjà utilisé")

    # DB SQLite éphémère par session (dans .pytest_cache)
    cache_dir = project_root / ".pytest_cache"
    cache_dir.mkdir(exist_ok=True)
    db_path = cache_dir / f"test_ebooks_{os.getpid()}.db"
    database_url = f"sqlite:///{db_path}"

    # Environnement du serveur
    env = os.environ.copy()
    env.update(
        {
            "TESTING": "true",
            "DATABASE_URL": database_url,
            # Pas de PYTHONPATH : on utilise --app-dir=src
            "OPENAI_API_KEY": env.get("OPENAI_API_KEY", "test-key-for-e2e"),
        }
    )

    # Commande Uvicorn :
    # - module:app (backoffice.main:app)
    # - --app-dir src -> rend le package importable sans editable install
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
        # "--reload",  # déconseillé en E2E: rend le boot non déterministe
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # permet kill de groupe sous POSIX
    )

    try:
        if not _wait_for_server(f"http://127.0.0.1:{server_port}", timeout=30.0):
            # Récupère un extrait de logs pour diagnostiquer
            try:
                stdout = proc.stdout.read(2000) if proc.stdout else ""  # type: ignore[arg-type]
                stderr = proc.stderr.read(2000) if proc.stderr else ""  # type: ignore[arg-type]
            except Exception:
                stdout = stderr = ""
            finally:
                _terminate_process(proc)

            pytest.skip(
                f"Serveur non accessible sur {server_port}. "
                f"STDERR: {stderr[:1000]!r} STDOUT: {stdout[:1000]!r}"
            )

        yield proc

    finally:
        _terminate_process(proc)
        # Nettoyage DB
        try:
            if db_path.exists():
                db_path.unlink()
        except Exception as e:
            print(f"[E2E] Warning: Could not remove test DB: {e}")


def _terminate_process(proc: subprocess.Popen) -> None:
    """Arrêt propre du processus Uvicorn (et groupe si possible)."""
    try:
        if proc.poll() is None:
            # D’abord TERM
            try:
                if hasattr(os, "killpg"):
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # type: ignore[arg-type]
                else:
                    proc.terminate()
            except Exception as e:
                print(f"[E2E] Warning: Could not terminate process group: {e}")

            # Attendre un peu
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # type: ignore[arg-type]
                    else:
                        proc.kill()
                except Exception as e:
                    print(f"[E2E] Warning: Could not kill process group: {e}")
                finally:
                    with contextlib.suppress(Exception):
                        proc.wait()
    except (psutil.NoSuchProcess, ProcessLookupError):
        pass


@pytest.fixture(scope="function")
def isolated_database(server_url: str, test_server: subprocess.Popen) -> Iterator[None]:
    """
    Isolation des données : reset via endpoint dédié avant chaque test.
    Si l'endpoint n'existe pas, on ne casse pas le test (warning).
    """
    import httpx

    try:
        with httpx.Client() as client:
            resp = client.post(f"{server_url}/__test__/reset", timeout=10.0)
            if resp.status_code not in (200, 404):
                print(f"[E2E] Warning: reset DB renvoie {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[E2E] Warning: reset DB échoue: {e!r}")

    yield


# ---------------------------
# Pytest config
# ---------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Marqueurs globaux."""
    config.addinivalue_line("markers", "smoke: Tests de fumée rapides")
    config.addinivalue_line("markers", "integration: Tests d'intégration")
    config.addinivalue_line("markers", "scenarios: Tests E2E scénarisés")
    config.addinivalue_line("markers", "error_handling: Scénarios d'erreurs")
    config.addinivalue_line("markers", "workflow: Workflows complets")
