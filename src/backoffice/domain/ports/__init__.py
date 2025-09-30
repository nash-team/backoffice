"""Domain ports (interfaces for external dependencies)."""

from backoffice.domain.ports.assembly_port import AssembledPage, AssemblyPort
from backoffice.domain.ports.content_page_generation_port import ContentPageGenerationPort
from backoffice.domain.ports.cover_generation_port import CoverGenerationPort

__all__ = [
    "AssembledPage",
    "AssemblyPort",
    "ContentPageGenerationPort",
    "CoverGenerationPort",
]
