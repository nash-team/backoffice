import logging
from enum import Enum

from backoffice.domain.entities.theme_profile import ThemeProfile

logger = logging.getLogger(__name__)


class AgeGroup(Enum):
    """Age group classifications for content adjustment"""

    TODDLER = "3-5"
    EARLY_READER = "6-8"
    PRE_TEEN = "9-12"

    @classmethod
    def from_string(cls, age_str: str) -> "AgeGroup":
        """Convert string to AgeGroup enum"""
        age_mapping = {
            "3-5": cls.TODDLER,
            "6-8": cls.EARLY_READER,
            "9-12": cls.PRE_TEEN,
        }
        return age_mapping.get(age_str, cls.EARLY_READER)  # Default to early reader

    def get_audience_hint(self) -> str:
        """Get audience-appropriate content hint"""
        return {
            AgeGroup.TODDLER: "toddler-friendly, very simple",
            AgeGroup.EARLY_READER: "early readers, kid-friendly",
            AgeGroup.PRE_TEEN: "pre-teen appropriate, slightly more detailed",
        }[self]


class EbookType(Enum):
    """Type of ebook being generated"""

    STORY = "story"
    COLORING = "coloring"


class PromptBuilder:
    """Service for building prompts using theme configuration"""

    def build_cover_prompt(
        self,
        theme: ThemeProfile,
        ebook_type: EbookType,
        age_group: AgeGroup,
        custom_subject: str | None = None,
    ) -> str:
        """
        Build a complete cover prompt using theme configuration

        Args:
            theme: Theme profile to use
            ebook_type: Type of ebook (story or coloring)
            age_group: Target age group
            custom_subject: Optional custom subject override

        Returns:
            Complete prompt string
        """
        logger.debug(
            f"Building cover prompt for theme '{theme.id}', type '{ebook_type.value}', "
            f"age '{age_group.value}'"
        )

        # Determine book type description
        type_block = self._get_type_description(ebook_type)

        # Get age-appropriate content hint
        audience_hint = age_group.get_audience_hint()

        # Use custom subject or theme default
        subject = custom_subject or theme.blocks.subject

        # Build palette description
        palette_line = self._build_palette_description(theme.palette)

        # Compose prompt in stable order: global → subject → environment → palette →
        # quality → negatives
        prompt_parts = [
            f"Professional {type_block} illustration featuring {subject}.",
            "Single page cover design, centered main character.",
            f"{theme.blocks.environment}.",
            f"{theme.blocks.tone}, {audience_hint}.",
            palette_line,
            ", ".join(theme.blocks.positives) + ".",
            ", ".join(theme.blocks.negatives) + ".",
        ]

        prompt = " ".join(prompt_parts)

        logger.debug(f"Generated prompt: {prompt[:100]}...")
        return prompt

    def build_page_prompt(
        self,
        theme: ThemeProfile,
        age_group: AgeGroup,
        page_description: str,
        is_cover: bool = False,
    ) -> str:
        """
        Build a prompt for individual pages using theme configuration

        Args:
            theme: Theme profile to use
            age_group: Target age group
            page_description: Description of the specific page content
            is_cover: Whether this is a cover page

        Returns:
            Complete prompt string
        """
        logger.debug(
            f"Building page prompt for theme '{theme.id}', age '{age_group.value}', "
            f"cover: {is_cover}"
        )

        # Get age-appropriate content hint
        audience_hint = age_group.get_audience_hint()

        # Build palette description
        palette_line = self._build_palette_description(theme.palette)

        # Compose prompt with page-specific content
        if is_cover:
            prompt_parts = [
                f"Professional coloring book cover illustration featuring {page_description}.",
                "Single page cover design, centered composition.",
                f"{theme.blocks.environment}.",
                f"{theme.blocks.tone}, {audience_hint}.",
                palette_line,
                ", ".join(theme.blocks.positives) + ".",
                ", ".join(theme.blocks.negatives) + ".",
            ]
        else:
            prompt_parts = [
                f"Coloring book page illustration featuring {page_description}.",
                f"Based on {theme.blocks.subject} theme.",
                f"{theme.blocks.environment}.",
                f"{theme.blocks.tone}, {audience_hint}.",
                palette_line,
                ", ".join(theme.blocks.positives) + ".",
                ", ".join(theme.blocks.negatives) + ".",
            ]

        prompt = " ".join(prompt_parts)

        logger.debug(f"Generated page prompt: {prompt[:100]}...")
        return prompt

    def _get_type_description(self, ebook_type: EbookType) -> str:
        """Get type-specific description"""
        return {
            EbookType.COLORING: "coloring book cover",
            EbookType.STORY: "children's storybook cover",
        }[ebook_type]

    def _build_palette_description(self, palette) -> str:
        """Build palette constraint description"""
        palette_parts = []

        if palette.base:
            palette_parts.append(f"Natural palette: {', '.join(palette.base)}")

        if palette.accents_allowed:
            palette_parts.append(f"accents allowed: {', '.join(palette.accents_allowed)}")

        if palette.forbidden_keywords:
            palette_parts.append(f"Avoid: {', '.join(palette.forbidden_keywords)}")

        return "; ".join(palette_parts) + "." if palette_parts else "Natural color palette."

    def get_age_appropriate_adjustments(self, age_group: AgeGroup) -> dict[str, str]:
        """Get age-specific content adjustments"""
        return {
            AgeGroup.TODDLER: {
                "complexity": "very simple shapes and forms",
                "details": "minimal details, large elements",
                "safety": "no small parts, rounded edges",
            },
            AgeGroup.EARLY_READER: {
                "complexity": "moderate detail level",
                "details": "engaging but not overwhelming",
                "safety": "age-appropriate content",
            },
            AgeGroup.PRE_TEEN: {
                "complexity": "more detailed and intricate",
                "details": "fine details acceptable",
                "safety": "slightly more complex themes OK",
            },
        }[age_group]
