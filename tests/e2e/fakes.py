"""
Fake implementations for E2E tests.

These fakes replace real external API calls with deterministic, instant responses.
This makes E2E tests fast, reliable, and repeatable without consuming API credits.
"""

from __future__ import annotations

import base64
from typing import Any

from backoffice.domain.entities.generation_request import ImageSpec
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort


# Fake 1x1 transparent PNG (smallest valid PNG)
FAKE_PNG_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def _create_fake_image_data() -> bytes:
    """Create a fake 1x1 transparent PNG image."""
    return base64.b64decode(FAKE_PNG_BASE64)


class FakeCoverGenerationPort(CoverGenerationPort):
    """Fake cover generation that returns instant deterministic results."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_prompt: str | None = None

    async def generate_cover(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a fake cover instantly."""
        self.call_count += 1
        self.last_prompt = prompt

        # Return fake PNG image data
        return _create_fake_image_data()

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return True


class FakeContentPageGenerationPort(ContentPageGenerationPort):
    """Fake content page generation for coloring pages that returns instant deterministic results."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_prompts: list[str] = []

    async def generate_page(
        self,
        prompt: str,
        spec: ImageSpec,
        seed: int | None = None,
    ) -> bytes:
        """Generate a fake content page instantly."""
        self.call_count += 1
        self.last_prompts.append(prompt)

        # Return fake PNG image data
        return _create_fake_image_data()

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return True

    def supports_vectorization(self) -> bool:
        """Check if provider supports SVG vectorization."""
        return False


def setup_fake_providers(app: Any) -> dict[str, Any]:
    """
    Setup fake providers in the FastAPI app for E2E tests.

    Returns a dict of fake instances for verification in tests.
    """

    fake_cover_gen = FakeCoverGenerationPort()
    fake_content_gen = FakeContentPageGenerationPort()

    # Store original dependencies
    original_deps = app.dependency_overrides.copy()

    # Override with fakes
    # Note: We need to find the actual dependency functions used in the app
    # For now, we'll document the pattern - actual implementation depends on your DI setup

    fakes = {
        "cover_generator": fake_cover_gen,
        "content_generator": fake_content_gen,
        "original_deps": original_deps,
    }

    return fakes


def teardown_fake_providers(app: Any, fakes: dict[str, Any]) -> None:
    """Restore original dependencies after tests."""
    app.dependency_overrides.clear()
    if "original_deps" in fakes:
        app.dependency_overrides.update(fakes["original_deps"])
