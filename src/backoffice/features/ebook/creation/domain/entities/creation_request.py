"""Creation request value object for ebook creation feature."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CreationRequest:
    """Value object representing an ebook creation request.

    This encapsulates all parameters needed to create a new ebook,
    with validation rules enforced in __post_init__.

    Business rules:
    - Only 'coloring' ebook type is supported currently
    - theme_id must be provided and non-empty
    - audience must be provided and non-empty
    - number_of_pages must be positive
    - title is optional (will be auto-generated if not provided)
    - author defaults to 'Assistant IA'
    - preview_mode defaults to False
    """

    ebook_type: str
    theme_id: str
    audience: str
    title: str | None = None
    author: str = "Assistant IA"
    number_of_pages: int = 8
    preview_mode: bool = False

    def __post_init__(self) -> None:
        """Validate business rules."""
        # Business rule: Only coloring type supported
        if self.ebook_type != "coloring":
            raise ValueError(
                f"Invalid ebook_type '{self.ebook_type}'. "
                f"Only 'coloring' type is currently supported."
            )

        # Business rule: theme_id required and non-empty
        if not self.theme_id or not self.theme_id.strip():
            raise ValueError("theme_id is required and cannot be empty")

        # Business rule: audience required and non-empty
        if not self.audience or not self.audience.strip():
            raise ValueError("audience is required and cannot be empty")

        # Business rule: number_of_pages must be positive
        if self.number_of_pages <= 0:
            raise ValueError(f"number_of_pages must be positive, got {self.number_of_pages}")
