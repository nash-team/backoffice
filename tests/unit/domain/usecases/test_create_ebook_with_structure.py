import pytest
from unittest.mock import AsyncMock, Mock

from backoffice.domain.entities.ebook import Ebook, EbookConfig, EbookStatus
from backoffice.domain.usecases.create_ebook import CreateEbookUseCase


class TestCreateEbookWithStructure:
    """Test cases for CreateEbookUseCase with chapter/page structure parameters"""

    @pytest.fixture
    def mock_ebook_repository(self):
        """Mock ebook repository"""
        repo = Mock()
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_ebook_processor(self):
        """Mock ebook processor"""
        processor = Mock()
        processor.generate_ebook_from_prompt = AsyncMock()
        return processor

    @pytest.fixture
    def create_ebook_usecase(self, mock_ebook_repository, mock_ebook_processor):
        """CreateEbookUseCase instance with mocked dependencies"""
        return CreateEbookUseCase(mock_ebook_repository, mock_ebook_processor)

    @pytest.mark.asyncio
    async def test_create_ebook_with_chapters(
        self, create_ebook_usecase, mock_ebook_processor, mock_ebook_repository
    ):
        """Test creating ebook with specified number of chapters"""
        # Arrange
        prompt = "Create a story about adventures"
        number_of_chapters = 5

        mock_ebook_processor.generate_ebook_from_prompt.return_value = {
            "title": "Adventure Story",
            "author": "Assistant IA",
            "drive_id": "test-drive-id",
            "preview_url": "https://example.com/preview",
        }

        mock_ebook_repository.create.return_value = Ebook(
            id=1,
            title="Adventure Story",
            author="Assistant IA",
            status=EbookStatus.DRAFT,
            created_at=None,
        )

        # Act
        result = await create_ebook_usecase.execute(
            prompt=prompt, number_of_chapters=number_of_chapters
        )

        # Assert
        assert result.title == "Adventure Story"

        # Verify config was created with correct chapter count
        call_args = mock_ebook_processor.generate_ebook_from_prompt.call_args
        config = call_args.kwargs["config"]
        assert config.number_of_chapters == 5
        assert config.number_of_pages is None

    @pytest.mark.asyncio
    async def test_create_ebook_with_pages(
        self, create_ebook_usecase, mock_ebook_processor, mock_ebook_repository
    ):
        """Test creating ebook with specified number of pages"""
        # Arrange
        prompt = "Create coloring pages with animals"
        number_of_pages = 10

        mock_ebook_processor.generate_ebook_from_prompt.return_value = {
            "title": "Animal Coloring Book",
            "author": "Assistant IA",
            "drive_id": "test-drive-id",
            "preview_url": "https://example.com/preview",
        }

        mock_ebook_repository.create.return_value = Ebook(
            id=1,
            title="Animal Coloring Book",
            author="Assistant IA",
            status=EbookStatus.DRAFT,
            created_at=None,
        )

        # Act
        result = await create_ebook_usecase.execute(prompt=prompt, number_of_pages=number_of_pages)

        # Assert
        assert result.title == "Animal Coloring Book"

        # Verify config was created with correct page count
        call_args = mock_ebook_processor.generate_ebook_from_prompt.call_args
        config = call_args.kwargs["config"]
        assert config.number_of_pages == 10
        assert config.number_of_chapters is None

    @pytest.mark.asyncio
    async def test_create_ebook_with_both_chapters_and_pages(
        self, create_ebook_usecase, mock_ebook_processor, mock_ebook_repository
    ):
        """Test creating ebook with both chapters and pages specified"""
        # Arrange
        prompt = "Create mixed content with stories and coloring"
        number_of_chapters = 3
        number_of_pages = 6

        mock_ebook_processor.generate_ebook_from_prompt.return_value = {
            "title": "Mixed Content Book",
            "author": "Assistant IA",
            "drive_id": "test-drive-id",
            "preview_url": "https://example.com/preview",
        }

        mock_ebook_repository.create.return_value = Ebook(
            id=1,
            title="Mixed Content Book",
            author="Assistant IA",
            status=EbookStatus.DRAFT,
            created_at=None,
        )

        # Act
        result = await create_ebook_usecase.execute(
            prompt=prompt, number_of_chapters=number_of_chapters, number_of_pages=number_of_pages
        )

        # Assert
        assert result.title == "Mixed Content Book"

        # Verify config was created with both counts
        call_args = mock_ebook_processor.generate_ebook_from_prompt.call_args
        config = call_args.kwargs["config"]
        assert config.number_of_chapters == 3
        assert config.number_of_pages == 6

    @pytest.mark.asyncio
    async def test_create_ebook_with_existing_config(
        self, create_ebook_usecase, mock_ebook_processor, mock_ebook_repository
    ):
        """Test creating ebook with existing config and additional structure parameters"""
        # Arrange
        prompt = "Create a story"
        existing_config = EbookConfig(toc=False, cover_enabled=False)
        number_of_chapters = 4

        mock_ebook_processor.generate_ebook_from_prompt.return_value = {
            "title": "Story Book",
            "author": "Assistant IA",
            "drive_id": "test-drive-id",
            "preview_url": "https://example.com/preview",
        }

        mock_ebook_repository.create.return_value = Ebook(
            id=1,
            title="Story Book",
            author="Assistant IA",
            status=EbookStatus.DRAFT,
            created_at=None,
        )

        # Act
        result = await create_ebook_usecase.execute(
            prompt=prompt, config=existing_config, number_of_chapters=number_of_chapters
        )

        # Assert
        assert result.title == "Story Book"

        # Verify config was updated with chapter count while preserving existing settings
        call_args = mock_ebook_processor.generate_ebook_from_prompt.call_args
        config = call_args.kwargs["config"]
        assert config.number_of_chapters == 4
        assert config.toc is False  # Original setting preserved
        assert config.cover_enabled is False  # Original setting preserved

    @pytest.mark.asyncio
    async def test_create_ebook_without_structure_params(
        self, create_ebook_usecase, mock_ebook_processor, mock_ebook_repository
    ):
        """Test creating ebook without structure parameters (default behavior)"""
        # Arrange
        prompt = "Create a general ebook"

        mock_ebook_processor.generate_ebook_from_prompt.return_value = {
            "title": "General Book",
            "author": "Assistant IA",
            "drive_id": "test-drive-id",
            "preview_url": "https://example.com/preview",
        }

        mock_ebook_repository.create.return_value = Ebook(
            id=1,
            title="General Book",
            author="Assistant IA",
            status=EbookStatus.DRAFT,
            created_at=None,
        )

        # Act
        result = await create_ebook_usecase.execute(prompt=prompt)

        # Assert
        assert result.title == "General Book"

        # Verify config was created with default values (no structure specified)
        call_args = mock_ebook_processor.generate_ebook_from_prompt.call_args
        config = call_args.kwargs["config"]
        assert config.number_of_chapters is None
        assert config.number_of_pages is None
