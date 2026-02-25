"""Unit tests for PromptTemplateEngine (Chicago style with fakes)."""

import pytest
import yaml

from backoffice.features.ebook.shared.domain.services.prompt_template_engine import (
    CharacterProfile,
    PromptTemplate,
    PromptTemplateEngine,
    SpeciesProfile,
)

# === Fixtures ===


@pytest.fixture
def themes_dir(tmp_path):
    """Create a temporary themes directory with test theme files."""
    themes = tmp_path / "themes"
    themes.mkdir()
    return themes


@pytest.fixture
def _basic_theme(themes_dir):
    """Create a basic theme YAML file (side-effect fixture)."""
    theme_content = {
        "id": "test_theme",
        "label": "Test Theme",
        "coloring_page_templates": {
            "default": {
                "base_structure": "A {ANIMAL} {ACTION} in a {ENV}.",
                "variables": {
                    "ANIMAL": ["cat", "dog", "bird"],
                    "ACTION": ["running", "sleeping", "playing"],
                    "ENV": ["park", "house", "forest"],
                },
                "quality_settings": "Black and white line art, simple outlines.",
            }
        },
        "cover_templates": {
            "default": {
                "prompt_blocks": {
                    "subject": "A cute animal",
                    "environment": "colorful background",
                    "tone": "kid-friendly",
                    "positives": ["detailed", "professional"],
                    "negatives": ["text", "mockup"],
                }
            }
        },
    }
    theme_file = themes_dir / "test_theme.yml"
    with open(theme_file, "w") as f:
        yaml.dump(theme_content, f)
    return theme_file


@pytest.fixture
def _theme_with_species_profiles(themes_dir):
    """Create a theme with species_profiles for constrained generation (side-effect fixture)."""
    theme_content = {
        "id": "dinosaurs",
        "label": "Dinosaurs",
        "coloring_page_templates": {
            "default": {
                "base_structure": "A {SPECIES} {ACTION} in a {ENV}.",
                "variables": {
                    "SPECIES": ["T-Rex", "Pteranodon", "Diplodocus"],
                    "ACTION": ["roaring", "flying", "eating leaves", "swimming"],
                    "ENV": ["jungle", "sky", "river", "volcanic plain"],
                },
                "species_profiles": {
                    "T-Rex": {
                        "actions": ["roaring", "eating meat", "running"],
                        "environments": ["volcanic plain", "jungle"],
                    },
                    "Pteranodon": {
                        "actions": ["flying", "gliding", "diving"],
                        "environments": ["sky", "coastal cliffs"],
                    },
                    "Diplodocus": {
                        "actions": ["eating leaves", "walking", "sleeping"],
                        "environments": ["jungle", "river"],
                    },
                },
                "quality_settings": "Black and white coloring page.",
            }
        },
    }
    theme_file = themes_dir / "dinosaurs.yml"
    with open(theme_file, "w") as f:
        yaml.dump(theme_content, f)
    return theme_file


@pytest.fixture
def _theme_with_direct_prompt(themes_dir):
    """Create a theme with direct prompt (no variables, side-effect fixture)."""
    theme_content = {
        "id": "simple_theme",
        "label": "Simple Theme",
        "coloring_page_templates": {
            "diffusers": {
                "prompt": "ColoringBookAF, cute animal, simple line art, white background",
                "workflow_params": {
                    "negative_prompt": "color, shading",
                    "guidance_scale": "7.5",
                },
            }
        },
    }
    theme_file = themes_dir / "simple_theme.yml"
    with open(theme_file, "w") as f:
        yaml.dump(theme_content, f)
    return theme_file


@pytest.fixture
def _theme_with_multiple_templates(themes_dir):
    """Create a theme with multiple template variations (side-effect fixture)."""
    theme_content = {
        "id": "multi_theme",
        "label": "Multi Theme",
        "coloring_page_templates": {
            "default": {
                "base_structure": "Default {ANIMAL}.",
                "variables": {"ANIMAL": ["cat"]},
                "quality_settings": "Default quality.",
            },
            "comfy": {
                "base_structure": "ComfyUI {ANIMAL}.",
                "variables": {"ANIMAL": ["dog"]},
                "quality_settings": "ComfyUI quality.",
            },
        },
    }
    theme_file = themes_dir / "multi_theme.yml"
    with open(theme_file, "w") as f:
        yaml.dump(theme_content, f)
    return theme_file


# === Tests ===


class TestPromptTemplateEngineInit:
    """Test cases for PromptTemplateEngine initialization."""

    def test_init_with_valid_themes_directory(self, themes_dir, _basic_theme):
        """Test initialization with valid themes directory."""
        # Act
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Assert
        assert engine.themes_directory == themes_dir
        assert engine.seed is None

    def test_init_with_seed(self, themes_dir, _basic_theme):
        """Test initialization with seed for reproducibility."""
        # Act
        engine = PromptTemplateEngine(seed=42, themes_directory=themes_dir)

        # Assert
        assert engine.seed == 42

    def test_init_with_invalid_directory_fails(self, tmp_path):
        """Test initialization fails with invalid themes directory."""
        # Arrange
        invalid_dir = tmp_path / "nonexistent"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            PromptTemplateEngine(themes_directory=invalid_dir)


class TestPromptTemplateEngineLoadTemplate:
    """Test cases for loading templates from YAML."""

    def test_load_coloring_page_template(self, themes_dir, _basic_theme):
        """Test loading coloring page template from YAML."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("test_theme")

        # Assert
        assert template.base_structure == "A {ANIMAL} {ACTION} in a {ENV}."
        assert "ANIMAL" in template.variables
        assert len(template.variables["ANIMAL"]) == 3
        assert "Black and white" in template.quality_settings

    def test_load_cover_template(self, themes_dir, _basic_theme):
        """Test loading cover template from YAML."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("test_theme", template_type="cover")

        # Assert
        assert "cute animal" in template.base_structure.lower()
        assert template.workflow_params is not None
        assert "negative" in template.workflow_params

    def test_load_template_with_specific_key(self, themes_dir, _theme_with_multiple_templates):
        """Test loading template with specific template key."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("multi_theme", template_key="comfy")

        # Assert
        assert "ComfyUI" in template.base_structure

    def test_load_template_falls_back_to_default(self, themes_dir, _theme_with_multiple_templates):
        """Test that unknown template key falls back to default."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("multi_theme", template_key="nonexistent")

        # Assert
        assert "Default" in template.base_structure

    def test_load_nonexistent_theme_fails(self, themes_dir, _basic_theme):
        """Test loading nonexistent theme raises error."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            engine.load_template_from_yaml("nonexistent_theme")

    def test_load_template_with_direct_prompt(self, themes_dir, _theme_with_direct_prompt):
        """Test loading template with direct prompt (no variables)."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("simple_theme", template_key="diffusers")

        # Assert
        assert "ColoringBookAF" in template.base_structure
        assert template.variables == {}  # No variables
        assert template.workflow_params is not None
        assert template.workflow_params["guidance_scale"] == "7.5"

    def test_load_template_with_species_profiles(self, themes_dir, _theme_with_species_profiles):
        """Test loading template with species_profiles."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        template = engine.load_template_from_yaml("dinosaurs")

        # Assert
        assert template.species_profiles is not None
        assert "T-Rex" in template.species_profiles
        assert "flying" in template.species_profiles["Pteranodon"].actions
        assert "sky" in template.species_profiles["Pteranodon"].environments


class TestPromptTemplateEngineGeneratePrompts:
    """Test cases for prompt generation."""

    def test_generate_prompts_count(self, themes_dir, _basic_theme):
        """Test generating specified number of prompts."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="test_theme", count=5)

        # Assert
        assert len(prompts) == 5

    def test_generate_prompts_replaces_variables(self, themes_dir, _basic_theme):
        """Test that variables are replaced in prompts."""
        # Arrange
        engine = PromptTemplateEngine(seed=42, themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="test_theme", count=1)

        # Assert
        assert "{ANIMAL}" not in prompts[0]
        assert "{ACTION}" not in prompts[0]
        assert "{ENV}" not in prompts[0]
        # Should contain actual values
        assert any(animal in prompts[0] for animal in ["cat", "dog", "bird"])

    def test_generate_prompts_includes_quality_settings(self, themes_dir, _basic_theme):
        """Test that quality settings are appended to prompts."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="test_theme", count=1)

        # Assert
        assert "Black and white" in prompts[0] or "line art" in prompts[0]

    def test_generate_prompts_with_seed_is_reproducible(self, themes_dir, _basic_theme):
        """Test that same seed produces same prompts."""
        # Arrange
        engine1 = PromptTemplateEngine(seed=42, themes_directory=themes_dir)
        engine2 = PromptTemplateEngine(seed=42, themes_directory=themes_dir)

        # Act
        prompts1 = engine1.generate_prompts(theme="test_theme", count=3)
        prompts2 = engine2.generate_prompts(theme="test_theme", count=3)

        # Assert
        assert prompts1 == prompts2

    def test_generate_prompts_different_seeds_different_results(self, themes_dir, _basic_theme):
        """Test that different seeds produce different prompts."""
        # Arrange
        engine1 = PromptTemplateEngine(seed=42, themes_directory=themes_dir)
        engine2 = PromptTemplateEngine(seed=999, themes_directory=themes_dir)

        # Act
        prompts1 = engine1.generate_prompts(theme="test_theme", count=10)
        prompts2 = engine2.generate_prompts(theme="test_theme", count=10)

        # Assert - at least some prompts should differ
        assert prompts1 != prompts2

    def test_generate_prompts_with_audience_children(self, themes_dir, _basic_theme):
        """Test prompt generation with children audience."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="test_theme", count=1, audience="children")

        # Assert
        assert "children" in prompts[0].lower() or "kid" in prompts[0].lower()

    def test_generate_prompts_with_audience_adults(self, themes_dir, _basic_theme):
        """Test prompt generation with adult audience."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="test_theme", count=1, audience="adults")

        # Assert
        assert "adult" in prompts[0].lower() or "intricate" in prompts[0].lower()


class TestPromptTemplateEngineSpeciesProfiles:
    """Test cases for species profiles (semantic constraints)."""

    def test_species_profiles_constrain_actions(self, themes_dir, _theme_with_species_profiles):
        """Test that species profiles constrain valid actions."""
        # Arrange
        engine = PromptTemplateEngine(seed=42, themes_directory=themes_dir)

        # Act - Generate many prompts and collect actions used for each species
        prompts = engine.generate_prompts(theme="dinosaurs", count=50)

        # Check T-Rex prompts don't have flying
        trex_prompts = [p for p in prompts if "T-Rex" in p]
        for prompt in trex_prompts:
            assert "flying" not in prompt.lower()

        # Check Pteranodon prompts have flying-related actions
        pteranodon_prompts = [p for p in prompts if "Pteranodon" in p]
        for prompt in pteranodon_prompts:
            # Should have flying-related actions, not eating leaves
            assert "eating leaves" not in prompt.lower()

    def test_species_profiles_constrain_environments(self, themes_dir, _theme_with_species_profiles):
        """Test that species profiles constrain valid environments."""
        # Arrange
        engine = PromptTemplateEngine(seed=42, themes_directory=themes_dir)

        # Act
        prompts = engine.generate_prompts(theme="dinosaurs", count=50)

        # Check T-Rex prompts don't have sky environment
        trex_prompts = [p for p in prompts if "T-Rex" in p]
        for prompt in trex_prompts:
            # T-Rex shouldn't be in the sky
            assert "in a sky" not in prompt.lower() or "sky" not in prompt.split("in a")[-1].split()[0].lower()


class TestPromptTemplateEngineWithParams:
    """Test cases for generate_prompts_with_params method."""

    def test_generate_prompts_with_params(self, themes_dir, _theme_with_direct_prompt):
        """Test generating prompts with workflow params."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        result = engine.generate_prompts_with_params(
            theme="simple_theme",
            count=2,
            template_key="diffusers",
        )

        # Assert
        assert "prompts" in result
        assert "workflow_params" in result
        assert len(result["prompts"]) == 2
        assert result["workflow_params"]["guidance_scale"] == "7.5"


class TestPromptTemplateEngineCoverPrompt:
    """Test cases for cover prompt generation."""

    def test_generate_cover_prompt(self, themes_dir, _basic_theme):
        """Test generating cover prompt."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        result = engine.generate_cover_prompt(theme="test_theme")

        # Assert
        assert "prompt" in result
        assert "workflow_params" in result
        assert "cute animal" in result["prompt"].lower()

    def test_generate_cover_prompt_includes_workflow_params(self, themes_dir, _basic_theme):
        """Test that cover prompt includes workflow params."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act
        result = engine.generate_cover_prompt(theme="test_theme")

        # Assert
        assert result["workflow_params"] is not None
        assert "negative" in result["workflow_params"]


class TestPromptTemplateEnginePartialMatch:
    """Test cases for theme partial matching."""

    def test_partial_theme_match(self, themes_dir, _basic_theme):
        """Test that partial theme names work."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act - Use partial name "test" to match "test_theme"
        prompts = engine.generate_prompts(theme="test", count=1)

        # Assert
        assert len(prompts) == 1

    def test_no_theme_match_fails(self, themes_dir, _basic_theme):
        """Test that completely unknown theme raises error."""
        # Arrange
        engine = PromptTemplateEngine(themes_directory=themes_dir)

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            engine.generate_prompts(theme="xyz_unknown_123", count=1)


class TestPromptTemplateDataClasses:
    """Test cases for data classes."""

    def test_character_profile_creation(self):
        """Test CharacterProfile creation."""
        # Act
        profile = CharacterProfile(
            actions=["running", "jumping"],
            environments=["park", "forest"],
        )

        # Assert
        assert profile.actions == ["running", "jumping"]
        assert profile.environments == ["park", "forest"]

    def test_species_profile_alias(self):
        """Test that SpeciesProfile is an alias for CharacterProfile."""
        # Assert
        assert SpeciesProfile is CharacterProfile

    def test_prompt_template_creation(self):
        """Test PromptTemplate creation."""
        # Act
        template = PromptTemplate(
            base_structure="A {ANIMAL}.",
            variables={"ANIMAL": ["cat", "dog"]},
            quality_settings="High quality.",
            workflow_params={"key": "value"},
            species_profiles={"cat": CharacterProfile(actions=["meow"], environments=["home"])},
        )

        # Assert
        assert template.base_structure == "A {ANIMAL}."
        assert len(template.variables["ANIMAL"]) == 2
        assert template.workflow_params["key"] == "value"
        assert "cat" in template.species_profiles

    def test_prompt_template_defaults(self):
        """Test PromptTemplate default values."""
        # Act
        template = PromptTemplate(
            base_structure="Test",
            variables={},
            quality_settings="",
        )

        # Assert
        assert template.workflow_params is None
        assert template.species_profiles is None
