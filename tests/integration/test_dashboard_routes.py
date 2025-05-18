import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import datetime
from domain.entities.ebook import Ebook, EbookStatus

# Configuration du client de test
client = TestClient(app)

def test_get_stats():
    """Test de récupération des statistiques"""
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    assert "Ebooks en attente" in response.text
    assert "Ebooks validés" in response.text

def test_get_ebooks():
    """Test de récupération de la liste des ebooks"""
    response = client.get("/api/dashboard/ebooks")
    assert response.status_code == 200
    assert "<td>" in response.text  # Vérifie qu'il y a au moins une cellule

def test_get_ebooks_with_status():
    """Test de récupération des ebooks filtrés par statut"""
    response = client.get("/api/dashboard/ebooks?status=pending")
    assert response.status_code == 200
    assert "<td>" in response.text

def test_get_new_ebook_form():
    """Test de récupération du formulaire de création d'ebook"""
    response = client.get("/api/dashboard/ebooks/new")
    assert response.status_code == 200
    assert "form" in response.text
    assert "textarea" in response.text
    assert "prompt" in response.text 