#!/usr/bin/env python3
"""
Parse GitHub issue body and create ebook generation specification.

This script extracts data from a GitHub issue created with the ebook-generation template
and generates a YAML specification file for the ebook generation pipeline.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import yaml


def get_github_token() -> str:
    """Get GitHub token from environment variable."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is required")
    return token


def fetch_issue(issue_number: int, repo: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch issue data from GitHub API.

    Args:
        issue_number: Issue number to fetch
        repo: Repository in format "owner/repo". If not provided, uses GITHUB_REPOSITORY env var

    Returns:
        Issue data as dictionary
    """
    if not repo:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise ValueError("Repository not specified and GITHUB_REPOSITORY not set")

    token = get_github_token()
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def parse_issue_body(body: str) -> Dict[str, Any]:
    """
    Parse the issue body to extract form data.

    GitHub Issues with forms have a specific format in the body.
    This function extracts the values from that format.

    Args:
        body: Issue body text

    Returns:
        Dictionary with parsed values
    """
    data = {}

    # Pattern to match form fields
    # Format: ### Field Name\n\nValue
    patterns = {
        "title": r"### Titre du livre\s*\n\s*\n\s*(.+)",
        "theme": r"### Thème\s*\n\s*\n\s*(.+)",
        "theme_description": r"### Description du nouveau thème\s*\n\s*\n\s*([\s\S]*?)(?=###|$)",
        "page_count": r"### Nombre de pages\s*\n\s*\n\s*(\d+)",
        "target_audience": r"### Public cible\s*\n\s*\n\s*(.+)",
        "language": r"### Langue\s*\n\s*\n\s*(\w+)",
        "special_instructions": r"### Instructions spéciales\s*\n\s*\n\s*([\s\S]*?)(?=###|$)",
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, body, re.MULTILINE)
        if match:
            value = match.group(1).strip()
            # Clean up "No response" or "_No response_" values
            if value in ["_No response_", "No response", ""]:
                value = None
            data[field] = value

    # Parse checkboxes (they appear as - [x] or - [ ])
    confirmations = []
    checkbox_pattern = r"- \[([x ])\] (.+)"
    for match in re.finditer(checkbox_pattern, body):
        if match.group(1) == "x":
            confirmations.append(match.group(2))
    data["confirmations"] = confirmations

    return data


def create_specification(issue_data: Dict[str, Any], parsed_body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create ebook specification from issue data and parsed body.

    Args:
        issue_data: Raw issue data from GitHub API
        parsed_body: Parsed form data from issue body

    Returns:
        Complete specification dictionary
    """
    # Determine if this is a new theme request
    is_new_theme = parsed_body.get("theme") == "[NOUVEAU] Créer un nouveau thème"

    # Generate theme slug
    if is_new_theme and parsed_body.get("theme_description"):
        # Extract key words from description to create a slug
        desc_words = parsed_body["theme_description"].lower().split()[:3]
        theme_slug = "_".join(word for word in desc_words if word.isalnum())
    else:
        theme_slug = parsed_body.get("theme", "default")

    spec = {
        "issue_number": issue_data["number"],
        "title": parsed_body.get("title", "Untitled"),
        "theme": theme_slug,
        "is_new_theme": is_new_theme,
        "theme_description": parsed_body.get("theme_description") if is_new_theme else None,
        "page_count": int(parsed_body.get("page_count", 24)),
        "target_audience": parsed_body.get("target_audience", "Enfants 6-10 ans"),
        "language": parsed_body.get("language", "fr"),
        "special_instructions": parsed_body.get("special_instructions"),
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "requested_by": issue_data["user"]["login"],
            "issue_url": issue_data["html_url"],
            "month": datetime.now().strftime("%Y-%m"),
        },
        "build": {
            "seed": "${GITHUB_SHA}",  # Will be replaced at build time
            "model": "gemini-2.5-flash",
            "resolution": 300,
            "format": "kdp",
            "trim_width_inches": 8.0,
            "trim_height_inches": 10.0,
            "bleed_inches": 0.125,
        },
        "drive": {
            "folder_structure": f"Ebooks/{datetime.now().year}/{datetime.now().strftime('%m-%B')}/ebook-{issue_data['number']}-{theme_slug}",
        },
        "confirmations": parsed_body.get("confirmations", []),
    }

    return spec


def validate_specification(spec: Dict[str, Any]) -> None:
    """
    Validate that the specification has all required fields.

    Args:
        spec: Specification dictionary

    Raises:
        ValueError: If validation fails
    """
    required_fields = ["issue_number", "title", "theme", "page_count", "target_audience"]

    for field in required_fields:
        if field not in spec or spec[field] is None:
            raise ValueError(f"Required field '{field}' is missing or empty")

    # Validate page count
    if not 24 <= spec["page_count"] <= 30:
        raise ValueError(f"Page count must be between 24 and 30, got {spec['page_count']}")

    # Validate confirmations
    if len(spec.get("confirmations", [])) < 3:
        raise ValueError("All confirmations must be checked before proceeding")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse GitHub issue and create ebook specification"
    )
    parser.add_argument("--issue-number", type=int, required=True, help="GitHub issue number")
    parser.add_argument("--repo", help="Repository (owner/repo format)")
    parser.add_argument("--output", required=True, help="Output YAML file path")
    parser.add_argument("--validate", action="store_true", help="Validate specification")

    args = parser.parse_args()

    try:
        # Fetch issue from GitHub
        print(f"Fetching issue #{args.issue_number}...")
        issue_data = fetch_issue(args.issue_number, args.repo)

        # Check if issue has the correct label
        labels = [label["name"] for label in issue_data.get("labels", [])]
        if "ebook-generation" not in labels:
            raise ValueError(f"Issue #{args.issue_number} does not have 'ebook-generation' label")

        # Parse issue body
        print("Parsing issue body...")
        parsed_body = parse_issue_body(issue_data["body"])

        # Create specification
        print("Creating specification...")
        spec = create_specification(issue_data, parsed_body)

        # Validate if requested
        if args.validate:
            print("Validating specification...")
            validate_specification(spec)

        # Create output directory if it doesn't exist
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write specification to file
        print(f"Writing specification to {args.output}...")
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        print(f"✅ Specification created successfully: {args.output}")

        # Print summary
        print("\n📚 Ebook Specification Summary:")
        print(f"  Title: {spec['title']}")
        print(f"  Theme: {spec['theme']}")
        print(f"  Pages: {spec['page_count']}")
        print(f"  Language: {spec['language']}")
        print(f"  Requested by: {spec['metadata']['requested_by']}")

        if spec["is_new_theme"]:
            print(f"  ⚠️  New theme requested - needs creation and validation")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
