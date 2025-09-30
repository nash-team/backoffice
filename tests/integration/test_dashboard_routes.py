import pytest
from datetime import datetime
from src.backoffice.infrastructure.models.ebook_model import EbookModel
from src.backoffice.domain.entities.ebook import EbookStatus


@pytest.fixture
def sample_ebooks(test_db_session):
    """Fixture pour créer des ebooks de test"""
    ebook1 = EbookModel(
        title="Test Ebook 1",
        author="Test Author 1",
        status=EbookStatus.PENDING.value,
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


def test_get_stats(test_client, sample_ebooks):
    """Test de récupération des statistiques"""
    response = test_client.get("/api/dashboard/stats")
    assert response.status_code == 200
    assert "En attente" in response.text
    assert "Approuvés" in response.text
    assert "1" in response.text  # 1 ebook en attente
    assert "1" in response.text  # 1 ebook validé


def test_get_ebooks(test_client, sample_ebooks):
    """Test de récupération de la liste des ebooks"""
    response = test_client.get("/api/dashboard/ebooks")
    assert response.status_code == 200
    assert "<td>" in response.text  # Vérifie qu'il y a au moins une cellule
    assert "Test Ebook 1" in response.text
    assert "Test Ebook 2" in response.text


def test_get_ebooks_with_status(test_client, sample_ebooks):
    """Test de récupération des ebooks filtrés par statut"""
    response = test_client.get("/api/dashboard/ebooks?status=pending")
    assert response.status_code == 200
    assert "<td>" in response.text
    assert "Test Ebook 1" in response.text
    assert "Test Ebook 2" not in response.text  # Ebook validé ne doit pas apparaître


def test_get_new_ebook_form(test_client):
    """Test de récupération du formulaire de création d'ebook (coloriage uniquement)"""
    response = test_client.get("/api/dashboard/ebooks/new")
    assert response.status_code == 200
    assert "form" in response.text
    # Verify coloring book specific fields
    assert "theme_id" in response.text
    assert "audience" in response.text
    assert "number_of_pages" in response.text
