import pytest

from backoffice.domain.entities.ebook import EbookConfig
from backoffice.domain.entities.ebook_structure import (
    EbookCover,
    EbookMeta,
    EbookSection,
    EbookStructure,
)
from backoffice.domain.usecases.generate_ebook import GenerateEbookUseCase


class FakeContentGenerator:
    """Fake content generator for testing"""

    def __init__(self, available: bool = True):
        self._available = available

    def is_available(self) -> bool:
        return self._available

    async def generate_ebook_structure(self, prompt: str) -> EbookStructure:
        """Generate fake ebook structure"""
        return EbookStructure(
            meta=EbookMeta(title=f"Test Book: {prompt[:20]}", author="Test Author"),
            cover=EbookCover(title="Test Cover"),
            sections=[
                EbookSection(type="chapter", title="Chapter 1", content_md="Test content 1"),
                EbookSection(type="chapter", title="Chapter 2", content_md="Test content 2"),
            ],
        )

    async def generate_ebook_content_legacy(self, prompt: str) -> dict[str, str]:
        return {
            "title": f"Legacy: {prompt[:20]}",
            "content": "Legacy content",
            "author": "Legacy Author",
        }


class FakeEbookGenerator:
    """Fake ebook generator for testing"""

    def __init__(self, supported_formats: list[str] = None):
        self.supported_formats = supported_formats or ["pdf"]

    def supports_format(self, format_type: str) -> bool:
        return format_type.lower() in self.supported_formats

    def get_supported_formats(self) -> list[str]:
        return self.supported_formats

    def generate_ebook(self, ebook_structure: EbookStructure, config: EbookConfig) -> bytes:
        """Generate fake ebook bytes"""
        content = f"FAKE {config.format.upper()} CONTENT for '{ebook_structure.meta.title}'"
        return content.encode()


class FakeFileStorage:
    """Fake file storage for testing"""

    def __init__(self, available: bool = True):
        self._available = available
        self.uploaded_files = []

    def is_available(self) -> bool:
        return self._available

    async def upload_ebook(
        self, file_bytes: bytes, filename: str, metadata: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Fake upload that stores file info"""
        file_info = {
            "id": f"fake-id-{len(self.uploaded_files)}",
            "url": f"https://fake-storage.com/{filename}",
            "filename": filename,
            "size": str(len(file_bytes)),
            "status": "uploaded",
        }
        self.uploaded_files.append(
            {"info": file_info, "bytes": file_bytes, "metadata": metadata or {}}
        )
        return file_info

    async def get_file_info(self, file_id: str) -> dict[str, str]:
        return {"id": file_id, "status": "exists"}


class TestGenerateEbookUseCase:
    """Tests for GenerateEbookUseCase using London style with fakes."""

    def test_given_dependencies_when_initializing_then_sets_up_use_case(self):
        # Given
        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator()
        file_storage = FakeFileStorage()

        # When
        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # Then
        assert use_case.content_generator == content_generator
        assert use_case.ebook_generator == ebook_generator
        assert use_case.file_storage == file_storage

    @pytest.mark.asyncio
    async def test_given_valid_prompt_when_executing_then_generates_and_uploads_ebook(self):
        # Given
        prompt = "Guide to machine learning"
        config = EbookConfig(format="pdf", toc_title="Contents")

        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When
        result = await use_case.execute(prompt, config)

        # Then
        assert "title" in result
        assert "Test Book: Guide to machine" in result["title"]
        assert result["author"] == "Test Author"
        assert result["format"] == "pdf"
        assert int(result["size"]) > 0
        assert result["content_generation_available"] is True
        assert result["storage_available"] is True
        assert "id" in result  # From storage upload
        assert len(file_storage.uploaded_files) == 1

    @pytest.mark.asyncio
    async def test_given_unsupported_format_when_executing_then_raises_value_error(self):
        # Given
        prompt = "Test prompt"
        config = EbookConfig(format="epub")  # Not supported by fake generator

        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])  # Only supports PDF
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When/Then
        with pytest.raises(Exception, match="Ebook generation failed"):
            await use_case.execute(prompt, config)

    @pytest.mark.asyncio
    async def test_given_no_storage_when_executing_then_generates_without_upload(self):
        # Given
        prompt = "Test prompt"
        config = EbookConfig(format="pdf")

        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, None)

        # When
        result = await use_case.execute(prompt, config)

        # Then
        assert result["storage_available"] is False
        assert result["storage_id"] is None
        assert result["storage_url"] is None
        assert result["storage_status"] == "no_storage"

    @pytest.mark.asyncio
    async def test_given_unavailable_storage_when_executing_then_skips_upload(self):
        # Given
        prompt = "Test prompt"
        config = EbookConfig(format="pdf")

        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])
        file_storage = FakeFileStorage(available=False)

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When
        result = await use_case.execute(prompt, config)

        # Then
        assert result["storage_available"] is False
        assert result["storage_id"] is None
        assert len(file_storage.uploaded_files) == 0

    @pytest.mark.asyncio
    async def test_given_default_config_when_executing_then_uses_defaults(self):
        # Given
        prompt = "Test prompt"

        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When
        result = await use_case.execute(prompt)  # No config provided

        # Then
        assert result["format"] == "pdf"  # Default format
        assert int(result["size"]) > 0

    def test_given_use_case_when_getting_supported_formats_then_returns_generator_formats(self):
        # Given
        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf", "epub", "mobi"])
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When
        formats = use_case.get_supported_formats()

        # Then
        assert formats == ["pdf", "epub", "mobi"]

    def test_given_use_case_when_getting_service_status_then_returns_all_statuses(self):
        # Given
        content_generator = FakeContentGenerator(available=True)
        ebook_generator = FakeEbookGenerator()
        file_storage = FakeFileStorage(available=False)

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When
        status = use_case.get_service_status()

        # Then
        assert status["content_generator"] is True
        assert status["ebook_generator"] is True
        assert status["file_storage"] is False

    @pytest.mark.asyncio
    async def test_given_content_generation_error_when_executing_then_propagates_exception(self):
        # Given
        prompt = "Test prompt"
        config = EbookConfig(format="pdf")

        # Content generator that raises exception
        class FailingContentGenerator(FakeContentGenerator):
            async def generate_ebook_structure(self, prompt: str):
                raise Exception("Content generation failed")

        content_generator = FailingContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf"])
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When/Then
        with pytest.raises(Exception, match="Ebook generation failed"):
            await use_case.execute(prompt, config)

    @pytest.mark.asyncio
    async def test_given_multiple_formats_when_checking_support_then_validates_correctly(self):
        # Given
        content_generator = FakeContentGenerator()
        ebook_generator = FakeEbookGenerator(["pdf", "epub"])
        file_storage = FakeFileStorage()

        use_case = GenerateEbookUseCase(content_generator, ebook_generator, file_storage)

        # When/Then - PDF should work
        config_pdf = EbookConfig(format="pdf")
        result_pdf = await use_case.execute("Test prompt", config_pdf)
        assert result_pdf["format"] == "pdf"

        # When/Then - EPUB should work
        config_epub = EbookConfig(format="epub")
        result_epub = await use_case.execute("Test prompt", config_epub)
        assert result_epub["format"] == "epub"

        # When/Then - MOBI should fail
        config_mobi = EbookConfig(format="mobi")
        with pytest.raises(Exception, match="Ebook generation failed"):
            await use_case.execute("Test prompt", config_mobi)
