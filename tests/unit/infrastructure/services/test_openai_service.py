import asyncio
import json

import pytest

from backoffice.infrastructure.services.openai_service import OpenAIService


class FakeOpenAIResponse:
    """Fake OpenAI API response for testing"""

    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeChoice:
    """Fake OpenAI choice for testing"""

    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeMessage:
    """Fake OpenAI message for testing"""

    def __init__(self, content: str):
        self.content = content


class FakeChat:
    """Fake OpenAI chat for testing"""

    def __init__(self):
        self.completions = FakeChatCompletions()


class FakeOpenAIClient:
    """Fake OpenAI client for testing"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.chat = FakeChat()


class FakeChatCompletions:
    """Fake OpenAI chat completions for testing"""

    async def create(self, **kwargs) -> FakeOpenAIResponse:
        """Return fake response based on prompt"""
        messages = kwargs.get("messages", [])

        # Check if it's a title generation request
        user_message = next((msg["content"] for msg in messages if msg["role"] == "user"), "")

        if "titre" in user_message.lower() and "génère un titre" in user_message.lower():
            return FakeOpenAIResponse("Guide Pratique: Test Title")

        # Check if it's JSON generation request
        system_message = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
        if "JSON" in system_message and "format" in system_message:
            fake_json = {
                "meta": {
                    "title": "Test Ebook Title",
                    "subtitle": "Test Subtitle",
                    "author": "Assistant IA",
                    "language": "fr",
                    "genre": "éducatif",
                    "trim": "A4",
                    "cover_color": "#2c3e50",
                    "engine": "weasyprint",
                },
                "cover": {
                    "title": "Test Cover Title",
                    "subtitle": "Test Cover Subtitle",
                    "tagline": "Test tagline",
                    "image_url": None,
                },
                "toc": True,
                "sections": [
                    {
                        "type": "chapter",
                        "title": "Chapitre 1 — Introduction",
                        "content_md": "Contenu du chapitre 1 en markdown...",
                    },
                    {
                        "type": "chapter",
                        "title": "Chapitre 2 — Développement",
                        "content_md": "Contenu du chapitre 2 en markdown...",
                    },
                ],
                "back_cover": {
                    "blurb": "Résumé du livre test...",
                    "about_author": "À propos de l'auteur test...",
                },
            }
            return FakeOpenAIResponse(json.dumps(fake_json, ensure_ascii=False, indent=2))

        # Default content generation
        return FakeOpenAIResponse("""## Introduction

Ce guide a été généré à partir de votre demande test.

## Chapitre 1: Fondamentaux

Contenu du premier chapitre avec des exemples pratiques.

## Chapitre 2: Concepts Avancés

Développement des concepts plus complexes.

## Conclusion

Synthèse et perspectives d'approfondissement.""")


class TestOpenAIService:
    """Tests for OpenAIService using London style with fakes."""

    def test_given_api_key_when_initializing_then_creates_client(self, monkeypatch):
        # Given
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", FakeOpenAIClient
        )

        # When
        service = OpenAIService()

        # Then
        assert service.api_key == api_key
        assert service.client is not None
        assert isinstance(service.client, FakeOpenAIClient)

    def test_given_no_api_key_when_initializing_then_client_is_none(self, monkeypatch):
        # Given
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # When
        service = OpenAIService()

        # Then
        assert service.api_key is None
        assert service.client is None

    @pytest.mark.asyncio
    async def test_given_valid_prompt_when_generating_ebook_json_then_returns_structured_content(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", FakeOpenAIClient
        )

        service = OpenAIService()

        # When
        result = await service.generate_ebook_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        assert "meta" in json_content
        assert "sections" in json_content
        assert json_content["meta"]["title"] == "Test Ebook Title"
        assert len(json_content["sections"]) == 2

    @pytest.mark.asyncio
    async def test_given_no_client_when_generating_ebook_json_then_returns_mock_content(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        service = OpenAIService()

        # When
        result = await service.generate_ebook_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        assert "meta" in json_content
        assert "sections" in json_content
        assert "Guide Pratique" in json_content["meta"]["title"]

    @pytest.mark.asyncio
    async def test_given_api_error_when_generating_ebook_json_then_falls_back_to_mock(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)

        # Mock client that raises exception
        class FailingOpenAIClient:
            def __init__(self, api_key: str):
                self.api_key = api_key

            @property
            def chat(self):
                raise Exception("API connection failed")

        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", FailingOpenAIClient
        )

        service = OpenAIService()

        # When
        result = await service.generate_ebook_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        assert "meta" in json_content
        assert "Guide Pratique" in json_content["meta"]["title"]

    @pytest.mark.asyncio
    async def test_given_invalid_json_response_when_generating_ebook_json_then_falls_back_to_mock(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)

        # Mock client that returns invalid JSON
        class InvalidJSONClient:
            def __init__(self, api_key: str):
                self.api_key = api_key
                self.chat = InvalidChatCompletions()

        class InvalidChatCompletions:
            async def create(self, **kwargs):
                return FakeOpenAIResponse("{ invalid json content }")

        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", InvalidJSONClient
        )

        service = OpenAIService()

        # When
        result = await service.generate_ebook_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        assert "meta" in json_content
        assert "Guide Pratique" in json_content["meta"]["title"]

    @pytest.mark.asyncio
    async def test_given_valid_prompt_when_generating_ebook_content_then_returns_content_with_title(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)
        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", FakeOpenAIClient
        )

        service = OpenAIService()

        # When
        result = await service.generate_ebook_content(prompt)

        # Then
        assert "title" in result
        assert "content" in result
        assert "author" in result
        assert result["title"] == "Guide Pratique: Test Title"
        assert result["author"] == "Assistant IA"
        assert "Introduction" in result["content"]

    @pytest.mark.asyncio
    async def test_given_no_client_when_generating_ebook_content_then_returns_mock_content(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        service = OpenAIService()

        # When
        result = await service.generate_ebook_content(prompt)

        # Then
        assert "title" in result
        assert "content" in result
        assert "author" in result
        assert "Guide Pratique" in result["title"]
        assert result["author"] == "Assistant IA"

    @pytest.mark.asyncio
    async def test_given_api_error_when_generating_ebook_content_then_falls_back_to_mock(
        self, monkeypatch
    ):
        # Given
        prompt = "Guide pratique pour apprendre Python"
        api_key = "fake-api-key-123"
        monkeypatch.setenv("OPENAI_API_KEY", api_key)

        # Mock client that raises exception
        class FailingOpenAIClient:
            def __init__(self, api_key: str):
                self.api_key = api_key

            @property
            def chat(self):
                raise Exception("API connection failed")

        monkeypatch.setattr(
            "backoffice.infrastructure.services.openai_service.AsyncOpenAI", FailingOpenAIClient
        )

        service = OpenAIService()

        # When
        result = await service.generate_ebook_content(prompt)

        # Then
        assert "title" in result
        assert "content" in result
        assert "author" in result
        assert "Guide Pratique" in result["title"]

    @pytest.mark.asyncio
    async def test_given_short_prompt_when_generating_mock_json_then_extracts_keywords_for_title(
        self,
    ):
        # Given
        prompt = "Python basics tutorial"
        service = OpenAIService()

        # When
        result = await service._mock_generate_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        assert "Python Basics Tutorial" in json_content["meta"]["title"]

    @pytest.mark.asyncio
    async def test_given_long_prompt_when_generating_mock_json_then_truncates_title_keywords(self):
        # Given
        prompt = "Very long prompt with many words that should be truncated for title generation"
        service = OpenAIService()

        # When
        result = await service._mock_generate_json(prompt)

        # Then
        assert "content" in result
        json_content = json.loads(result["content"])
        # Should only take first 3 words
        assert "Very Long Prompt" in json_content["meta"]["title"]

    @pytest.mark.asyncio
    async def test_given_prompt_when_generating_mock_content_then_includes_processing_delay(self):
        # Given
        prompt = "Test prompt"
        service = OpenAIService()
        start_time = asyncio.get_event_loop().time()

        # When
        await service._mock_generate_content(prompt)

        # Then
        elapsed_time = asyncio.get_event_loop().time() - start_time
        # Should have at least 0.5 second delay
        assert elapsed_time >= 0.5

    @pytest.mark.asyncio
    async def test_given_mock_generation_when_creating_json_then_structure_is_valid(self):
        # Given
        prompt = "Machine learning guide"
        service = OpenAIService()

        # When
        result = await service._mock_generate_json(prompt)

        # Then
        json_content = json.loads(result["content"])

        # Verify complete structure
        assert "meta" in json_content
        assert "cover" in json_content
        assert "toc" in json_content
        assert "sections" in json_content
        assert "back_cover" in json_content

        # Verify meta structure
        meta = json_content["meta"]
        assert "title" in meta
        assert "author" in meta
        assert meta["author"] == "Assistant IA"
        assert meta["language"] == "fr"

        # Verify sections structure
        sections = json_content["sections"]
        assert len(sections) == 3
        for section in sections:
            assert "type" in section
            assert "title" in section
            assert "content_md" in section
            assert section["type"] == "chapter"

    @pytest.mark.asyncio
    async def test_given_mock_generation_when_creating_content_then_includes_original_prompt(self):
        # Given
        prompt = "Deep learning fundamentals"
        service = OpenAIService()

        # When
        result = await service._mock_generate_content(prompt)

        # Then
        assert prompt in result["content"]
        assert "Deep Learning Fundamentals" in result["title"]
