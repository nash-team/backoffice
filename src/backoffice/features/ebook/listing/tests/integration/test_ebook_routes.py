import pytest

pytestmark = pytest.mark.integration


def test_get_ebook_preview_success(test_client):
    """Test de récupération réussie de l'URL de prévisualisation"""
    response = test_client.get("/api/dashboard/drive/ebooks/test_drive_id")
    assert response.status_code == 200
    assert "https://drive.google.com/file/d/test_drive_id/preview" in response.text


def test_get_ebook_preview_not_found(test_client):
    """Test quand l'ID de l'ebook n'est pas valide"""
    response = test_client.get("/api/dashboard/drive/ebooks/non_existent_id")
    assert response.status_code == 200
    assert "non_existent_id" in response.text
