import pytest
from datetime import datetime
from domain.entities.ebook import Ebook, EbookStatus
from domain.usecases.get_stats import GetStatsUseCase
from infrastructure.adapters.in_memory_ebook_repository import InMemoryEbookRepository

@pytest.fixture
def repository():
    return InMemoryEbookRepository()

@pytest.fixture
def usecase(repository):
    return GetStatsUseCase(repository)

@pytest.fixture
async def sample_ebooks(repository):
    ebooks = [
        Ebook(1, "Python pour les débutants", "John Doe", datetime.now(), EbookStatus.PENDING),
        Ebook(2, "FastAPI Masterclass", "Jane Smith", datetime.now(), EbookStatus.VALIDATED),
        Ebook(3, "Django REST", "Alice Johnson", datetime.now(), EbookStatus.PENDING)
    ]
    for ebook in ebooks:
        await repository.save(ebook)
    return ebooks

@pytest.mark.asyncio
async def test_get_stats_with_sample_ebooks(usecase, sample_ebooks):
    # Given
    await sample_ebooks  # Attendre que les ebooks soient créés

    # When
    stats = await usecase.execute()

    # Then
    assert stats.total_ebooks == 3
    assert stats.pending_ebooks == 2
    assert stats.validated_ebooks == 1

@pytest.mark.asyncio
async def test_get_stats_with_empty_repository(usecase):
    # When
    stats = await usecase.execute()

    # Then
    assert stats.total_ebooks == 0
    assert stats.pending_ebooks == 0
    assert stats.validated_ebooks == 0 