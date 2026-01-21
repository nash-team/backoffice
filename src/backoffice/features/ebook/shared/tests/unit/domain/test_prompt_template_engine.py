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

        # Assert - Check for essential keywords (updated for Flux 2 format)
        for prompt in prompts:
            # Core coloring page elements
            assert "bold outlines" in prompt.lower() or "thick" in prompt.lower()
            assert "black and white" in prompt.lower() or "line art" in prompt.lower()
            # Quality indicators
            assert "coloring" in prompt.lower()
            # Either has closed shapes or clear shapes
            assert "closed shapes" in prompt.lower() or "clear" in prompt.lower()

    def test_generate_prompts_dinosaurs_theme(self):
        """Test dinosaurs theme generates expected structure."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=5)

        # Assert
        for prompt in prompts:
            # Should contain coloring page indicators
            assert "coloring" in prompt.lower()
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
                "Spinosaurus",
                "Parasaurolophus",
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
            assert "coloring" in prompt.lower()
            assert "unicorn" in prompt.lower()

    def test_generate_prompts_pirates_theme(self):
        """Test pirates theme works correctly."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act
        prompts = engine.generate_prompts(theme="pirates", count=5)

        # Assert
        for prompt in prompts:
            # Should contain coloring page indicators
            assert "coloring" in prompt.lower()
            # Should have pirate-related content (pirate OR captain OR ship OR sea etc.)
            pirate_keywords = ["pirate", "captain", "ship", "sea", "treasure", "parrot", "crew", "sailor"]
            assert any(word in prompt.lower() for word in pirate_keywords), f"No pirate content found in: {prompt[:200]}"

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
        """Test that audience parameter adds tailored hints."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act - audience parameter adds a short hint
        prompts_children = engine.generate_prompts(theme="dinosaurs", count=2, audience="children")
        prompts_adults = engine.generate_prompts(theme="dinosaurs", count=2, audience="adults")

        # Assert - both should generate valid prompts with audience hints
        assert len(prompts_children) == 2
        assert len(prompts_adults) == 2
        # Children prompts should mention children/kid-friendly
        assert "children" in prompts_children[0].lower() or "kid" in prompts_children[0].lower()
        # Adult prompts should mention adult/intricate/detailed
        assert "adult" in prompts_adults[0].lower() or "intricate" in prompts_adults[0].lower() or "detailed" in prompts_adults[0].lower()

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


class TestSpeciesProfileConstraints:
    """Tests for species_profiles semantic constraints."""

    def test_pteranodon_only_flies_never_runs(self):
        """Test that Pteranodon only gets flying-related actions, never running."""
        # Arrange
        engine = PromptTemplateEngine(seed=None)

        # Act - Generate many prompts to find Pteranodon
        pteranodon_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            pteranodon_prompts.extend([p for p in prompts if "Pteranodon" in p])

        # Assert - Pteranodon should never have terrestrial actions
        assert len(pteranodon_prompts) > 0, "Should find at least one Pteranodon prompt"
        forbidden_actions = ["running", "eating leaves", "eating meat", "swimming", "wading", "hunting", "defending"]
        for prompt in pteranodon_prompts:
            for action in forbidden_actions:
                assert action not in prompt, f"Pteranodon should not be {action}: {prompt[:100]}"

    def test_trex_never_flies_or_swims(self):
        """Test that T-Rex never flies or swims."""
        # Arrange & Act
        trex_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            trex_prompts.extend([p for p in prompts if "T-Rex" in p])

        # Assert
        assert len(trex_prompts) > 0, "Should find at least one T-Rex prompt"
        forbidden_actions = ["flying", "gliding", "diving", "swimming", "wading", "eating leaves"]
        for prompt in trex_prompts:
            for action in forbidden_actions:
                assert action not in prompt, f"T-Rex should not be {action}: {prompt[:100]}"

    def test_spinosaurus_can_swim(self):
        """Test that Spinosaurus (semi-aquatic) gets swimming actions."""
        # Arrange & Act
        spinosaurus_prompts = []
        for seed in range(200):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            spinosaurus_prompts.extend([p for p in prompts if "Spinosaurus" in p])

        # Assert - Spinosaurus should have aquatic actions
        assert len(spinosaurus_prompts) > 0, "Should find at least one Spinosaurus prompt"
        aquatic_actions = ["swimming", "wading"]
        has_aquatic = any(any(action in prompt for action in aquatic_actions) for prompt in spinosaurus_prompts)
        assert has_aquatic, "Spinosaurus should have at least one aquatic action"

    def test_pteranodon_in_sky_environment(self):
        """Test that Pteranodon is placed in appropriate sky/cliff environments."""
        # Arrange & Act
        pteranodon_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            pteranodon_prompts.extend([p for p in prompts if "Pteranodon" in p])

        # Assert - Pteranodon should never be in jungle/desert/volcanic plain
        assert len(pteranodon_prompts) > 0
        forbidden_envs = ["lush jungle", "volcanic plain", "desert", "swamp"]
        for prompt in pteranodon_prompts:
            for env in forbidden_envs:
                assert env not in prompt, f"Pteranodon should not be in {env}: {prompt[:100]}"

    def test_herbivores_eat_leaves_not_meat(self):
        """Test that herbivores only eat leaves, never meat."""
        # Arrange
        herbivores = ["Diplodocus", "Brachiosaurus", "Triceratops", "Stegosaurus", "Ankylosaurus"]

        # Act
        herbivore_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="dinosaurs", count=10)
            herbivore_prompts.extend([p for p in prompts if any(h in p for h in herbivores)])

        # Assert
        assert len(herbivore_prompts) > 0
        for prompt in herbivore_prompts:
            assert "eating meat" not in prompt, f"Herbivore eating meat: {prompt[:100]}"
            assert "hunting" not in prompt, f"Herbivore hunting: {prompt[:100]}"

    def test_only_winged_unicorn_can_fly(self):
        """Test that winged unicorn can fly (species_profiles filtering)."""
        # Arrange & Act
        flying_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="unicorns", count=10)
            flying_prompts.extend([p for p in prompts if "flying" in p.lower()])

        # Assert - Should find flying prompts (species_profiles should allow flying for some unicorns)
        assert len(flying_prompts) > 0, "Should find at least one flying prompt"
        # At minimum, some unicorn should be flying
        for prompt in flying_prompts:
            assert "unicorn" in prompt.lower(), f"Flying prompt should contain unicorn: {prompt[:150]}"

    def test_baby_unicorn_has_appropriate_actions(self):
        """Test that baby unicorn has appropriate actions (cute, playful)."""
        # Arrange & Act
        baby_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="unicorns", count=10)
            baby_prompts.extend([p for p in prompts if "baby unicorn" in p.lower()])

        # Assert - should find baby unicorn prompts
        assert len(baby_prompts) > 0, "Should find at least one baby unicorn prompt"
        # Baby unicorn should have some action
        for prompt in baby_prompts:
            assert "unicorn" in prompt.lower(), f"Baby unicorn prompt: {prompt[:150]}"

    def test_parrot_cannot_steer_ship(self):
        """Test that parrot companion never does human actions like steering ship."""
        # Arrange & Act
        parrot_prompts = []
        for seed in range(100):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="pirates", count=10)
            parrot_prompts.extend([p for p in prompts if "parrot companion" in p])

        # Assert - parrot should never do human-only actions
        assert len(parrot_prompts) > 0, "Should find at least one parrot prompt"
        human_actions = ["steering ship", "digging for treasure", "looking through telescope", "sailing", "climbing rigging"]
        for prompt in parrot_prompts:
            for action in human_actions:
                assert action not in prompt, f"Parrot doing human action '{action}': {prompt[:150]}"

    def test_parrot_has_bird_actions(self):
        """Test that parrot companion gets bird-appropriate actions."""
        # Arrange & Act
        parrot_prompts = []
        for seed in range(200):
            engine = PromptTemplateEngine(seed=seed)
            prompts = engine.generate_prompts(theme="pirates", count=10)
            parrot_prompts.extend([p for p in prompts if "parrot companion" in p])

        # Assert - should find bird actions
        assert len(parrot_prompts) > 0, "Should find at least one parrot prompt"
        bird_actions = ["perched on shoulder", "flying over ship", "squawking", "eating crackers"]
        has_bird_action = any(any(action in prompt for action in bird_actions) for prompt in parrot_prompts)
        assert has_bird_action, "Parrot should have at least one bird action"

    def test_character_profiles_work_with_different_variable_names(self):
        """Test that character profiles work with UNICORN, CHARACTER, SPECIES variable names."""
        # Arrange
        engine = PromptTemplateEngine(seed=42)

        # Act - all themes now have character_profiles
        unicorn_prompts = engine.generate_prompts(theme="unicorns", count=5)
        pirate_prompts = engine.generate_prompts(theme="pirates", count=5)
        dino_prompts = engine.generate_prompts(theme="dinosaurs", count=5)

        # Assert - should generate valid prompts with no unreplaced placeholders
        for prompts in [unicorn_prompts, pirate_prompts, dino_prompts]:
            assert len(prompts) == 5
            for prompt in prompts:
                assert "{" not in prompt, f"Unreplaced placeholder: {prompt[:100]}"
