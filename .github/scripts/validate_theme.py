#!/usr/bin/env python3
"""
Validate and create theme profiles for ebook generation.

This script checks if a theme exists, creates it if necessary,
and validates it against the schema.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml
from jsonschema import ValidationError, validate


def get_github_token() -> str:
    """Get GitHub token from environment variable."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return token


def load_specification(spec_file: str) -> Dict[str, Any]:
    """Load ebook specification from YAML file."""
    with open(spec_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def theme_exists(theme_name: str) -> bool:
    """Check if a theme file exists."""
    theme_path = Path(f"themes/{theme_name}.yaml")
    return theme_path.exists()


def load_theme_schema() -> Dict[str, Any]:
    """Load theme validation schema."""
    schema_path = Path("themes/schema.json")
    if not schema_path.exists():
        # Return a default schema if file doesn't exist yet
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": ["name", "description", "color_palette", "visual_style", "base_prompts"],
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "color_palette": {
                    "type": "object",
                    "required": ["primary", "secondary", "accent"],
                    "properties": {
                        "primary": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                        "secondary": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                        "accent": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"},
                    },
                },
                "visual_style": {"type": "string"},
                "base_prompts": {
                    "type": "object",
                    "required": ["cover", "content"],
                    "properties": {"cover": {"type": "string"}, "content": {"type": "string"}},
                },
                "created_via": {"type": "string"},
                "approved_by": {"type": "string"},
                "created_at": {"type": "string", "format": "date"},
            },
        }

    with open(schema_path, "r") as f:
        return json.load(f)


def generate_theme_from_description(
    theme_name: str, description: str, issue_number: int
) -> Dict[str, Any]:
    """
    Generate a theme profile from a description.

    In a real implementation, this could use AI to generate better color palettes
    and prompts. For now, we'll create a reasonable default.

    Args:
        theme_name: Name/slug for the theme
        description: User's description of the theme
        issue_number: Issue number that requested this theme

    Returns:
        Theme dictionary
    """
    # Parse description for keywords
    description_lower = description.lower() if description else ""

    # Simple color palette generation based on keywords
    if "christmas" in description_lower or "noël" in description_lower:
        colors = {
            "primary": "#C41E3A",  # Christmas red
            "secondary": "#165B33",  # Christmas green
            "accent": "#FFD700",  # Gold
        }
    elif "halloween" in description_lower:
        colors = {
            "primary": "#FF6600",  # Orange
            "secondary": "#4B0082",  # Indigo
            "accent": "#000000",  # Black
        }
    elif "ocean" in description_lower or "mer" in description_lower:
        colors = {
            "primary": "#006994",  # Ocean blue
            "secondary": "#00CED1",  # Dark turquoise
            "accent": "#FFE4B5",  # Moccasin (sand)
        }
    elif "nature" in description_lower or "forest" in description_lower:
        colors = {
            "primary": "#228B22",  # Forest green
            "secondary": "#8B4513",  # Saddle brown
            "accent": "#FFD700",  # Gold
        }
    else:
        # Default pleasant palette
        colors = {
            "primary": "#4A90E2",  # Soft blue
            "secondary": "#50C878",  # Emerald
            "accent": "#FFA500",  # Orange
        }

    # Extract visual style from description
    visual_keywords = []
    style_words = [
        "moderne",
        "minimaliste",
        "détaillé",
        "simple",
        "complexe",
        "géométrique",
        "organique",
        "abstrait",
        "réaliste",
        "fantaisiste",
        "kawaii",
        "manga",
        "cartoon",
        "vintage",
        "rétro",
    ]

    for word in style_words:
        if word in description_lower:
            visual_keywords.append(word)

    visual_style = ", ".join(visual_keywords) if visual_keywords else "simple et moderne"

    # Create theme profile
    theme = {
        "name": theme_name,
        "description": description or f"Thème personnalisé créé depuis l'issue #{issue_number}",
        "color_palette": colors,
        "visual_style": visual_style,
        "base_prompts": {
            "cover": f"Create a coloring book cover with {visual_style} style. "
            f"Use a color scheme based on {colors['primary']}, {colors['secondary']}, and {colors['accent']}. "
            "The design should be appealing and professional.",
            "content": f"Create a simple line art coloring page with {visual_style} style. "
            "Black and white only, clear outlines, suitable for coloring. "
            "No shading, no filled areas, only contours.",
        },
        "created_via": f"github-issue-{issue_number}",
        "approved_by": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d"),
    }

    return theme


def validate_theme(theme_data: Dict[str, Any]) -> None:
    """
    Validate theme data against schema.

    Args:
        theme_data: Theme dictionary to validate

    Raises:
        ValidationError: If theme doesn't match schema
    """
    schema = load_theme_schema()
    validate(instance=theme_data, schema=schema)


def create_theme_file(theme_name: str, theme_data: Dict[str, Any]) -> str:
    """
    Create a theme file and commit it to the current branch.

    Args:
        theme_name: Name of the theme (used for filename)
        theme_data: Theme data dictionary

    Returns:
        Path to created file
    """
    # Ensure themes directory exists
    themes_dir = Path("themes")
    themes_dir.mkdir(exist_ok=True)

    # Write theme file
    theme_path = themes_dir / f"{theme_name}.yaml"
    with open(theme_path, "w", encoding="utf-8") as f:
        yaml.dump(theme_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Git operations
    subprocess.run(["git", "add", str(theme_path)], check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            f"feat: Add new theme '{theme_name}'\n\nCreated from issue description",
        ],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)

    return str(theme_path)


def add_pr_comment(pr_number: int, comment: str, repo: Optional[str] = None) -> None:
    """Add a comment to a pull request."""
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise ValueError("Repository not specified and GITHUB_REPOSITORY not set")

    token = get_github_token()
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    response = requests.post(url, headers=headers, json={"body": comment})
    response.raise_for_status()


def add_pr_label(pr_number: int, label: str, repo: Optional[str] = None) -> None:
    """Add a label to a pull request."""
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise ValueError("Repository not specified and GITHUB_REPOSITORY not set")

    token = get_github_token()
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/labels"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    response = requests.post(url, headers=headers, json={"labels": [label]})
    response.raise_for_status()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Validate or create theme for ebook generation")
    parser.add_argument("--spec", required=True, help="Path to specification YAML file")
    parser.add_argument("--pr-number", type=int, required=True, help="Pull request number")
    parser.add_argument("--repo", help="Repository (owner/repo format)")
    parser.add_argument(
        "--force-create", action="store_true", help="Force creation even if theme exists"
    )

    args = parser.parse_args()

    try:
        # Load specification
        print(f"Loading specification from {args.spec}...")
        spec = load_specification(args.spec)

        theme_name = spec["theme"]
        is_new_theme = spec.get("is_new_theme", False)

        print(f"Theme: {theme_name}")
        print(f"New theme requested: {is_new_theme}")

        # Check if theme exists
        if theme_exists(theme_name) and not args.force_create:
            print(f"✅ Theme '{theme_name}' already exists")

            # Load and validate existing theme
            with open(f"themes/{theme_name}.yaml", "r") as f:
                theme_data = yaml.safe_load(f)

            print("Validating existing theme...")
            validate_theme(theme_data)
            print("✅ Theme is valid")

            # Add comment to PR
            comment = (
                f"## ✅ Thème validé\n\nLe thème **{theme_name}** existe déjà et est valide.\n\n"
            )
            comment += "La génération peut continuer."
            add_pr_comment(args.pr_number, comment, args.repo)

        else:
            # Theme doesn't exist or force create requested
            if not is_new_theme and not args.force_create:
                raise ValueError(f"Theme '{theme_name}' does not exist but was not marked as new")

            print(f"Creating new theme '{theme_name}'...")

            # Generate theme from description
            theme_description = spec.get("theme_description", "")
            issue_number = spec["issue_number"]
            theme_data = generate_theme_from_description(
                theme_name, theme_description, issue_number
            )

            # Validate generated theme
            print("Validating new theme...")
            validate_theme(theme_data)

            # Create theme file and commit
            print("Creating theme file...")
            theme_path = create_theme_file(theme_name, theme_data)

            # Add label to PR
            add_pr_label(args.pr_number, "needs-theme-approval", args.repo)

            # Add comment to PR with theme details
            comment = f"## 🎨 Nouveau thème créé: **{theme_name}**\n\n"
            comment += "### Détails du thème\n"
            comment += f"**Description**: {theme_data['description']}\n\n"
            comment += f"**Style visuel**: {theme_data['visual_style']}\n\n"
            comment += "**Palette de couleurs**:\n"
            comment += f"- Principal: `{theme_data['color_palette']['primary']}`\n"
            comment += f"- Secondaire: `{theme_data['color_palette']['secondary']}`\n"
            comment += f"- Accent: `{theme_data['color_palette']['accent']}`\n\n"
            comment += "### ✅ Checklist\n"
            comment += "- [ ] Thème validé par un reviewer\n"
            comment += "- [ ] Couleurs appropriées\n"
            comment += "- [ ] Style cohérent\n\n"
            comment += f"📁 Fichier créé: `{theme_path}`\n\n"
            comment += (
                "**Action requise**: Veuillez réviser et approuver ce thème avant de continuer."
            )

            add_pr_comment(args.pr_number, comment, args.repo)

            print(f"✅ Theme '{theme_name}' created and committed")
            print("⚠️  Theme needs approval before ebook generation can continue")

        return 0

    except ValidationError as e:
        print(f"❌ Theme validation failed: {e.message}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
