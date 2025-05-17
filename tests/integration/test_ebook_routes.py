import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from domain.entities.ebook import Ebook, EbookStatus
import os
import sys

# Configuration du client de test
client = TestClient(app)

@pytest.fixture(autouse=True)
def override_get_ebook_source():
    adapter = MagicMock()
    adapter.get_ebook = AsyncMock()
    adapter.get_ebook.return_value = Ebook(
        id=0,
        title="Test Ebook",
        author="Test Author",
        created_at=datetime.now(),
        status=EbookStatus.PENDING,
        drive_id="test_drive_id",
        preview_url="https://drive.google.com/file/d/test_drive_id/preview"
    )
    def _get_ebook_source():
        return adapter
    import presentation.routes.ebook_routes
    app.dependency_overrides[presentation.routes.ebook_routes.get_ebook_source] = _get_ebook_source
    yield adapter
    app.dependency_overrides = {}

def test_get_ebook_success(override_get_ebook_source):
    """Test de récupération réussie d'un ebook"""
    response = client.get("/api/drive/ebooks/test_drive_id")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Ebook"
    assert data["author"] == "Test Author"
    assert data["drive_id"] == "test_drive_id"
    assert data["preview_url"] == "https://drive.google.com/file/d/test_drive_id/preview"

def test_get_ebook_not_found(override_get_ebook_source):
    """Test quand l'ebook n'est pas trouvé"""
    override_get_ebook_source.get_ebook.return_value = None
    response = client.get("/api/drive/ebooks/non_existent_id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ebook non trouvé"

def test_get_ebook_drive_error(override_get_ebook_source):
    """Test en cas d'erreur Google Drive"""
    override_get_ebook_source.get_ebook.side_effect = Exception("Erreur Google Drive")
    response = client.get("/api/drive/ebooks/test_drive_id")
    assert response.status_code == 500
    assert "Erreur" in response.json()["detail"] 