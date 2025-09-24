"""
Test de debug simple pour Playwright.
"""

import pytest
import requests


def test_simple_server_debug(simple_server_url):
    """Test simple pour débugger le serveur."""
    print(f"[TEST] Trying to connect to {simple_server_url}")

    # Test avec requests d'abord
    try:
        response = requests.get(f"{simple_server_url}/healthz", timeout=5)
        print(f"[TEST] Health check response: {response.status_code}")
        print(f"[TEST] Health check body: {response.text}")
        assert response.status_code == 200
    except Exception as e:
        print(f"[TEST] Health check failed: {e}")
        pytest.fail(f"Health check failed: {e}")


def test_simple_playwright_debug(page, simple_server_url):
    """Test simple avec Playwright."""
    print(f"[TEST] Trying to navigate to {simple_server_url} with Playwright")

    try:
        response = page.goto(simple_server_url, timeout=10000)
        print(f"[TEST] Playwright navigation response: {response}")
        print(f"[TEST] Page title: {page.title()}")
    except Exception as e:
        print(f"[TEST] Playwright navigation failed: {e}")
        raise
