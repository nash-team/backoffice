"""
Factory for test providers (fakes).

When USE_FAKE_PROVIDERS environment variable is set, returns fake implementations
instead of real API clients. This makes tests deterministic, fast, and cost-free.
"""

import os

from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort


def should_use_fakes() -> bool:
    """Check if we should use fake providers."""
    return os.getenv("USE_FAKE_PROVIDERS", "false").lower() == "true"


def create_cover_generation_port() -> CoverGenerationPort:
    """Create cover generation port (real or fake based on environment)."""
    if should_use_fakes():
        # Import here to avoid circular dependency and to only load when needed
        from tests.e2e.fakes import FakeCoverGenerationPort

        return FakeCoverGenerationPort()
    else:
        # Use real provider
        from backoffice.infrastructure.providers.openrouter_cover_provider import (
            OpenRouterCoverProvider,
        )

        return OpenRouterCoverProvider()


def create_content_page_generation_port() -> ContentPageGenerationPort:
    """Create content page generation port (real or fake based on environment)."""
    if should_use_fakes():
        # Import here to avoid circular dependency
        from tests.e2e.fakes import FakeContentPageGenerationPort

        return FakeContentPageGenerationPort()
    else:
        # Use real provider via factory
        from backoffice.infrastructure.providers.provider_factory import (
            ProviderFactory,
        )

        return ProviderFactory.create_content_page_provider()
