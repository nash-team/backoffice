"""Fake assembly port for testing."""

from pathlib import Path

from backoffice.features.ebook.shared.domain.errors.error_taxonomy import DomainError, ErrorCode
from backoffice.features.ebook.shared.domain.ports.assembly_port import AssembledPage, AssemblyPort


class FakeAssemblyPort(AssemblyPort):
    """Fake assembly port that simulates PDF generation.

    Configurable behavior:
    - succeed: Create fake PDF file
    - fail: Simulate assembly failure
    """

    def __init__(
        self,
        mode: str = "succeed",
    ):
        """Initialize fake port.

        Args:
            mode: Behavior mode (succeed, fail)
        """
        self.mode = mode
        self.call_count = 0
        self.last_cover = None
        self.last_pages = None
        self.last_output_path = None

    async def assemble_pdf(
        self,
        cover: AssembledPage,
        pages: list[AssembledPage],
        output_path: str,
    ) -> str:
        """Assemble fake PDF.

        Args:
            cover: Cover page
            pages: Content pages
            output_path: Output path

        Returns:
            URI to fake PDF

        Raises:
            DomainError: If mode is fail
        """
        self.call_count += 1
        self.last_cover = cover
        self.last_pages = pages
        self.last_output_path = output_path

        if self.mode == "fail":
            raise DomainError(
                code=ErrorCode.IMAGE_TOO_SMALL,
                message="Fake assembly failed",
                actionable_hint="Check fake configuration",
            )

        # Create fake PDF file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Write fake PDF content
        fake_pdf_content = b"%PDF-1.4\n%FAKE_PDF\n"
        fake_pdf_content += f"Cover: {cover.title}\n".encode()
        for page in pages:
            fake_pdf_content += f"Page {page.page_number}: {page.title}\n".encode()
        fake_pdf_content += b"%%EOF\n"

        output_file.write_bytes(fake_pdf_content)

        return f"file://{output_path}"
