from datetime import datetime

import pytest

from backoffice.features.shared.domain.entities.ebook import EbookStatus
from backoffice.features.shared.infrastructure.models.ebook_model import EbookModel

pytestmark = pytest.mark.integration


@pytest.fixture
def _sample_ebooks(test_db_session):
    """Fixture pour créer des ebooks de test"""
    ebook1 = EbookModel(
        title="Test Ebook 1",
        author="Test Author 1",
        status=EbookStatus.DRAFT.value,
        created_at=datetime.now(),
    )
    ebook2 = EbookModel(
        title="Test Ebook 2",
        author="Test Author 2",
        status=EbookStatus.APPROVED.value,
        created_at=datetime.now(),
    )

    test_db_session.add(ebook1)
    test_db_session.add(ebook2)
    test_db_session.commit()

    return [ebook1, ebook2]


def test_get_stats(test_client, _sample_ebooks):
    """Test de récupération des statistiques"""
    response = test_client.get("/api/dashboard/stats")
    assert response.status_code == 200
    assert "Brouillons" in response.text
    assert "Approuvés" in response.text
    assert "1" in response.text  # 1 ebook brouillon
    assert "1" in response.text  # 1 ebook approuvé


def test_get_ebooks(test_client, _sample_ebooks):
    """Test de récupération de la liste des ebooks"""
    response = test_client.get("/api/dashboard/ebooks")
    assert response.status_code == 200
    assert "<td>" in response.text  # Vérifie qu'il y a au moins une cellule
    assert "Test Ebook 1" in response.text
    assert "Test Ebook 2" in response.text


def test_get_ebooks_with_status(test_client, _sample_ebooks):
    """Test de récupération des ebooks filtrés par statut"""
    response = test_client.get("/api/dashboard/ebooks?status=draft")
    assert response.status_code == 200
    assert "<td>" in response.text
    assert "Test Ebook 1" in response.text
    assert "Test Ebook 2" not in response.text  # Ebook approuvé ne doit pas apparaître


def test_get_new_ebook_form(test_client):
    """Test de récupération du formulaire de création d'ebook (coloriage uniquement)"""
    response = test_client.get("/api/dashboard/ebooks/new")
    assert response.status_code == 200
    assert "form" in response.text
    # Verify coloring book specific fields
    assert "theme_id" in response.text
    assert "audience" in response.text
    assert "number_of_pages" in response.text
