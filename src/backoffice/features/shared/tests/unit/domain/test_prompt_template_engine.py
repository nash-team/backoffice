"""Unit tests for PromptTemplateEngine."""

import pytest

from backoffice.features.ebook.shared.domain.services.prompt_template_engine import (
    PromptTemplateEngine,
)


class TestPromptTemplateEngine:
    """Tests for PromptTemplateEngine."""

    def test_generate_prompts_with_seed_reproducibility(self):
        """Test that same seed produces same prompts."""
        # Arrange
        engine1 = PromptTemplateEngine(seed=42)
        engine2 = PromptTemplateEngine(seed=42)

        # Act
        prompts1 = engine1.generate_prompts(theme="dinosaurs", count=5)
        prompts2 = engine2.generate_prompts(theme="dinosaurs", count=5)

        # Assert
        assert len(prompts1) == 5
        assert len(prompts2) == 5
        assert prompts1 == prompts2  # Same seed = same prompts

    def test_generate_prompts_different_seeds_produce_variation(self):
        """Test that different seeds produce different prompts."""
        # Arrange
        engine1 = PromptTemplateEngine(seed=42)
        engine2 = PromptTemplateEngine(seed=99)

        # Act
        prompts1 = engine1.generate_prompts(theme="dinosaurs", count=5)
        prompts2 = engine2.generate_prompts(theme="dinosaurs", count=5)

        # Assert
        assert len(prompts1) == 5
        assert len(prompts2) == 5
        assert prompts1 != prompts2  # Different seeds = different prompts

    def test_generate_prompts_variety_within_same_book(self):
        """Test that pages within same book have variety."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=10)

        # Assert - Most prompts should be unique (allow some duplicates with small option sets)
        assert len(prompts) == 10
        assert len(set(prompts)) >= 8  # At least 80% unique

    def test_generate_prompts_contains_quality_settings(self):
        """Test that prompts contain essential quality settings."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=3)

        # Assert - Check for essential keywords
        for prompt in prompts:
            assert "Bold clean outlines" in prompt
            assert "closed shapes" in prompt
            assert "no shading" in prompt or "NO gray shading" in prompt  # Wording variation
            assert "NO gray" in prompt or "no gray" in prompt
            assert "NO color" in prompt or "no color" in prompt
            assert (
                "full page" in prompt or "Illustration extends naturally" in prompt
            )  # Wording variation
            assert "300 DPI" in prompt
            assert "No text" in prompt
            assert "no logo" in prompt
            assert "no watermark" in prompt

    def test_generate_prompts_dinosaurs_theme(self):
        """Test dinosaurs theme generates expected structure."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=5)

        # Assert
        for prompt in prompts:
            # Should contain "Line art coloring page"
            assert "Line art coloring page" in prompt
            # Should contain a dinosaur species (at least one of them)
            species = [
                "T-Rex",
                "Triceratops",
                "Diplodocus",
                "Stegosaurus",
                "Pteranodon",
                "Ankylosaurus",
                "Velociraptor",
                "Brachiosaurus",
            ]
            assert any(s in prompt for s in species)

    def test_generate_prompts_unicorns_theme(self):
        """Test unicorns theme works correctly."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="unicorns", count=5)

        # Assert
        for prompt in prompts:
            assert "Line art coloring page" in prompt
            assert "unicorn" in prompt

    def test_generate_prompts_pirates_theme(self):
        """Test pirates theme works correctly."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="pirates", count=5)

        # Assert
        for prompt in prompts:
            assert "Line art coloring page" in prompt
            # Should have pirate-related content (pirate OR parrot OR treasure)
            assert any(word in prompt.lower() for word in ["pirate", "parrot", "treasure"])
            # Should not have violence
            assert "no scary elements" in prompt
            assert "no violence" in prompt

    def test_generate_prompts_unknown_theme_raises_error(self):
        """Test that unknown theme raises FileNotFoundError with helpful message."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            engine.generate_prompts(theme="unknown_theme", count=3)

        # Check error message contains available themes
        assert "No template found for theme 'unknown_theme'" in str(exc_info.value)
        assert "Available themes:" in str(exc_info.value)

    def test_generate_prompts_partial_theme_match(self):
        """Test that partial theme name matches (e.g., 'dino' -> 'dinosaurs')."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts_full = engine.generate_prompts(theme="dinosaurs", count=5)
        prompts_partial = engine.generate_prompts(theme="dino", count=5)

        # Assert - Should use same template
        assert prompts_full == prompts_partial

    def test_generate_prompts_audience_parameter(self):
        """Test that audience parameter is accepted (for future use)."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act - audience parameter is optional and not currently used in prompt
        prompts_children = engine.generate_prompts(theme="dinosaurs", count=2, audience="children")
        prompts_adults = engine.generate_prompts(theme="dinosaurs", count=2, audience="adults")

        # Assert - both should generate valid prompts with quality settings from YAML
        assert len(prompts_children) == 2
        assert len(prompts_adults) == 2
        assert "Black and white line art" in prompts_children[0]
        assert "Black and white line art" in prompts_adults[0]

    def test_generate_prompts_zero_count(self):
        """Test generating zero prompts."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=0)

        # Assert
        assert len(prompts) == 0

    def test_generate_prompts_large_count(self):
        """Test generating large number of prompts."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=50)

        # Assert
        assert len(prompts) == 50
        # Should have variety (not all identical)
        assert len(set(prompts)) > 10

    def test_prompt_structure_completeness(self):
        """Test that generated prompts have all required components."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=5)

        # Assert
        for prompt in prompts:
            # Should have subject, action, environment
            assert len(prompt) > 100  # Reasonably long
            # Should not have template placeholders left
            assert "{" not in prompt
            assert "}" not in prompt

    def test_no_seed_produces_random_prompts(self):
        """Test that no seed produces different results on different runs."""
        # Arrange & Act - Generate multiple times without seed
        all_prompts = []
        for _ in range(5):
            engine = PromptTemplateEngine(seed=None)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            all_prompts.extend(prompts)

        # Assert - Should have variety (not all identical)
        # With many variables, should get good variety even with collisions
        unique_count = len(set(all_prompts))
        total_count = len(all_prompts)
        # At least 60% unique (allowing for some random collisions)
        assert unique_count >= total_count * 0.6
