from datetime import datetime

import pytest

from domain.entities.ebook import Ebook, EbookStatus
from domain.usecases.get_ebooks import GetEbooksUseCase
from infrastructure.adapters.in_memory_ebook_repository import InMemoryEbookRepository


@pytest.fixture
def repository():
    return InMemoryEbookRepository()


@pytest.fixture
def usecase(repository):
    return GetEbooksUseCase(repository)


@pytest.fixture
async def sample_ebooks(repository):
    ebooks = [
        Ebook(1, "Python pour les débutants", "John Doe", datetime.now(), EbookStatus.PENDING),
        Ebook(2, "FastAPI Masterclass", "Jane Smith", datetime.now(), EbookStatus.VALIDATED),
        Ebook(3, "Django REST", "Alice Johnson", datetime.now(), EbookStatus.PENDING),
    ]
    for ebook in ebooks:
        await repository.save(ebook)
    return ebooks


@pytest.mark.asyncio
async def test_get_all_ebooks(usecase, sample_ebooks):
    # Given
    await sample_ebooks  # Attendre que les ebooks soient créés

    # When
    ebooks = await usecase.execute()

    # Then
    assert len(ebooks) == 3
    assert all(isinstance(ebook, Ebook) for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_pending_ebooks(usecase, sample_ebooks):
    # Given
    await sample_ebooks  # Attendre que les ebooks soient créés

    # When
    ebooks = await usecase.execute(EbookStatus.PENDING)

    # Then
    assert len(ebooks) == 2
    assert all(ebook.status == EbookStatus.PENDING for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_validated_ebooks(usecase, sample_ebooks):
    # Given
    await sample_ebooks  # Attendre que les ebooks soient créés

    # When
    ebooks = await usecase.execute(EbookStatus.VALIDATED)

    # Then
    assert len(ebooks) == 1
    assert all(ebook.status == EbookStatus.VALIDATED for ebook in ebooks)


@pytest.mark.asyncio
async def test_get_ebooks_empty_repository(usecase):
    # When
    ebooks = await usecase.execute()

    # Then
    assert len(ebooks) == 0
