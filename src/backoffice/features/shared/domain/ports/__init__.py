"""Domain ports (interfaces for external dependencies)."""

from backoffice.features.shared.domain.ports.assembly_port import AssembledPage, AssemblyPort
from backoffice.features.shared.domain.ports.content_page_generation_port import (
    ContentPageGenerationPort,
)
from backoffice.features.shared.domain.ports.cover_generation_port import CoverGenerationPort

__all__ = [
    "AssembledPage",
    "AssemblyPort",
    "ContentPageGenerationPort",
    "CoverGenerationPort",
]
