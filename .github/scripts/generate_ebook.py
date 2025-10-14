#!/usr/bin/env python3
"""
Generate ebook from specification file for CI/CD pipeline.

This script wraps the existing ebook generation functionality
and adapts it for CI usage with deterministic builds.
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Add project root to path to import application modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backoffice.features.ebook.creation.domain.entities.creation_request import CreationRequest
from backoffice.features.ebook.creation.domain.usecases.create_ebook import CreateEbookUseCase
from backoffice.features.ebook.export.domain.usecases.export_ebook_pdf import ExportEbookPdfUseCase
from backoffice.features.ebook.export.domain.usecases.export_to_kdp import ExportToKdpUseCase
from backoffice.features.ebook.shared.domain.entities.ebook import Ebook, EbookStatus
from backoffice.features.ebook.shared.infrastructure.factories.repository_factory import (
    RepositoryFactory,
)
from backoffice.features.shared.infrastructure.database import get_async_session
from backoffice.features.shared.infrastructure.events.event_bus import EventBus


def load_specification(spec_file: str) -> Dict[str, Any]:
    """Load ebook specification from YAML file."""
    with open(spec_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    # Replace environment variables in spec
    if "build" in spec and "seed" in spec["build"]:
        spec["build"]["seed"] = os.environ.get("GITHUB_SHA", spec["build"]["seed"])

    return spec


def load_theme(theme_name: str) -> Dict[str, Any]:
    """Load theme data from theme file."""
    theme_path = Path(f"themes/{theme_name}.yaml")
    if not theme_path.exists():
        raise FileNotFoundError(f"Theme '{theme_name}' not found at {theme_path}")

    with open(theme_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_generation_request(spec: Dict[str, Any], theme: Dict[str, Any]) -> CreationRequest:
    """
    Create a generation request from specification and theme.

    Args:
        spec: Ebook specification
        theme: Theme data

    Returns:
        CreationRequest object
    """
    # Build the full prompt from theme and spec
    cover_prompt = theme["base_prompts"]["cover"]
    content_prompt = theme["base_prompts"]["content"]

    # Add special instructions if provided
    if spec.get("special_instructions"):
        cover_prompt += f"\n\nAdditional instructions: {spec['special_instructions']}"
        content_prompt += f"\n\nAdditional instructions: {spec['special_instructions']}"

    # Add title to cover prompt
    cover_prompt += f"\n\nTitle to include: {spec['title']}"

    request = CreationRequest(
        title=spec["title"],
        theme=spec["theme"],
        page_count=spec["page_count"],
        target_audience=spec.get("target_audience", "Children 6-10"),
        language=spec.get("language", "fr"),
        cover_prompt=cover_prompt,
        content_prompt=content_prompt,
        seed=spec["build"].get("seed"),
        model=spec["build"].get("model", "gemini-2.5-flash"),
        resolution=spec["build"].get("resolution", 300),
    )

    return request


async def generate_ebook(spec: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Generate ebook based on specification.

    Args:
        spec: Ebook specification
        output_dir: Output directory for generated files

    Returns:
        Dictionary with generation results and metrics
    """
    start_time = time.time()
    costs = {"tokens": 0, "estimated_usd": 0.0, "details": []}

    # Load theme
    print(f"Loading theme '{spec['theme']}'...")
    theme = load_theme(spec["theme"])

    # Create generation request
    print("Creating generation request...")
    request = create_generation_request(spec, theme)

    # Initialize dependencies
    print("Initializing dependencies...")
    async for session in get_async_session():
        factory = RepositoryFactory(session)
        event_bus = EventBus()

        # Create use cases
        create_usecase = CreateEbookUseCase(
            ebook_repository=factory.get_ebook_repository(), event_bus=event_bus
        )

        export_pdf_usecase = ExportEbookPdfUseCase(
            ebook_repository=factory.get_ebook_repository(), event_bus=event_bus
        )

        export_kdp_usecase = ExportToKdpUseCase(
            ebook_repository=factory.get_ebook_repository(), event_bus=event_bus
        )

        try:
            # Generate ebook
            print(f"Generating ebook with seed: {request.seed}...")
            ebook = await create_usecase.execute(request)
            print(f"Ebook created with ID: {ebook.id}")

            # Update costs (simplified - in real implementation, track from events)
            costs["tokens"] = 50000  # Estimate
            costs["estimated_usd"] = 0.25
            costs["details"].append({"step": "generation", "tokens": 50000, "cost": 0.25})

            # Export to PDF
            print("Exporting to PDF...")
            pdf_path = await export_pdf_usecase.execute(ebook.id)
            print(f"PDF exported: {pdf_path}")

            # Copy PDF to output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(pdf_path, output_dir / "interior.pdf")

            # Create preview version (for now, just copy - could compress later)
            shutil.copy(pdf_path, output_dir / "preview.pdf")

            # Extract cover if available
            if ebook.cover_image:
                cover_path = output_dir / "cover.pdf"
                # In real implementation, extract cover from ebook data
                # For now, create placeholder
                with open(cover_path, "wb") as f:
                    f.write(b"Cover PDF placeholder")

            # Export to KDP
            print("Creating KDP package...")
            kdp_path = await export_kdp_usecase.execute(ebook.id)
            if kdp_path:
                shutil.copy(kdp_path, output_dir / "kdp-package.zip")

            # Generate thumbnails (placeholder for now)
            thumbnails_dir = output_dir / "thumbnails"
            thumbnails_dir.mkdir(exist_ok=True)
            # In real implementation, generate PNG thumbnails from PDF pages

            # Calculate duration
            duration = time.time() - start_time

            # Create provenance file
            provenance = {
                "issue": spec["issue_number"],
                "title": spec["title"],
                "theme": spec["theme"],
                "timestamp": datetime.now().isoformat(),
                "build": {
                    "seed": request.seed,
                    "duration_seconds": duration,
                    "steps": [
                        "theme_validation",
                        "cover_generation",
                        "content_generation",
                        "pdf_assembly",
                        "kdp_export",
                    ],
                },
                "costs": costs,
                "models": {"cover": request.model, "content": request.model},
                "environment": {
                    "python": sys.version.split()[0],
                    "github_sha": os.environ.get("GITHUB_SHA", "local"),
                    "github_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
                },
                "outputs": {
                    "interior_pdf": "interior.pdf",
                    "cover_pdf": "cover.pdf",
                    "kdp_package": "kdp-package.zip",
                    "preview_pdf": "preview.pdf",
                },
            }

            # Write provenance
            with open(output_dir / "provenance.json", "w") as f:
                json.dump(provenance, f, indent=2)

            # Write costs
            with open(output_dir / "costs.json", "w") as f:
                json.dump(costs, f, indent=2)

            print(f"✅ Generation completed in {duration:.2f} seconds")
            print(f"💰 Estimated cost: ${costs['estimated_usd']:.4f}")

            return {
                "success": True,
                "ebook_id": ebook.id,
                "duration": duration,
                "costs": costs,
                "outputs": provenance["outputs"],
            }

        except Exception as e:
            print(f"❌ Generation failed: {e}")
            # Write error to provenance
            error_provenance = {
                "issue": spec["issue_number"],
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": time.time() - start_time,
            }
            with open(output_dir / "error.json", "w") as f:
                json.dump(error_provenance, f, indent=2)
            raise


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate ebook from specification")
    parser.add_argument("--spec", required=True, help="Path to specification YAML file")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated files")
    parser.add_argument("--seed", help="Override seed for generation")
    parser.add_argument("--dry-run", action="store_true", help="Validate without generating")

    args = parser.parse_args()

    try:
        # Load specification
        print(f"Loading specification from {args.spec}...")
        spec = load_specification(args.spec)

        # Override seed if provided
        if args.seed:
            spec["build"]["seed"] = args.seed

        # Validate theme exists
        theme_path = Path(f"themes/{spec['theme']}.yaml")
        if not theme_path.exists():
            raise FileNotFoundError(f"Theme '{spec['theme']}' not found")

        if args.dry_run:
            print("Dry run mode - validation only")
            print(f"  Title: {spec['title']}")
            print(f"  Theme: {spec['theme']}")
            print(f"  Pages: {spec['page_count']}")
            print(f"  Seed: {spec['build']['seed']}")
            print("✅ Validation successful")
            return 0

        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run async generation
        print("Starting ebook generation...")
        result = asyncio.run(generate_ebook(spec, output_dir))

        print("\n📚 Generation Summary:")
        print(f"  Ebook ID: {result['ebook_id']}")
        print(f"  Duration: {result['duration']:.2f}s")
        print(f"  Cost: ${result['costs']['estimated_usd']:.4f}")
        print(f"  Output directory: {output_dir}")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
