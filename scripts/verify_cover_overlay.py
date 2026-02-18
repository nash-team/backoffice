#!/usr/bin/env python3
"""Verify cover overlay placement by compositing onto a test image.

Usage:
    # With a real cover image:
    python scripts/verify_cover_overlay.py --cover path/to/cover.png --theme dinosaurs

    # With a generated placeholder (colored grid with guides):
    python scripts/verify_cover_overlay.py --theme dinosaurs

    # Specify output file:
    python scripts/verify_cover_overlay.py --theme dinosaurs -o my_test.png

    # Use custom dimensions (default: 1024x1024 for Flux/SDXL):
    python scripts/verify_cover_overlay.py --theme dinosaurs --width 2475 --height 3150
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from backoffice.features.ebook.shared.domain.services.cover_compositor import (
    COVER_DPI,
    FOOTER_MAX_HEIGHT_RATIO,
    KDP_BLEED_INCHES,
    KDP_SAFE_ZONE_INCHES,
    PADDING_PX,
    TITLE_MAX_HEIGHT_RATIO,
    CoverCompositor,
)


def _create_test_cover(width: int, height: int) -> Image.Image:
    """Create a test cover image with grid lines and zone indicators."""
    img = Image.new("RGB", (width, height), "#4a90d9")
    draw = ImageDraw.Draw(img)

    # Draw grid
    grid_step = width // 10
    for x in range(0, width, grid_step):
        draw.line([(x, 0), (x, height)], fill="#3a7bc8", width=1)
    for y in range(0, height, grid_step):
        draw.line([(0, y), (width, y)], fill="#3a7bc8", width=1)

    # Draw safe zone rectangle (red dashed)
    padding = PADDING_PX
    draw.rectangle(
        [padding, padding, width - padding, height - padding],
        outline="#ff4444",
        width=2,
    )

    # Draw overlay zones (where title/footer will land)
    # Title zone: top
    draw.rectangle(
        [padding, padding, width - padding, padding + height // 4],
        outline="#ffaa00",
        width=3,
    )
    # Footer zone: bottom
    draw.rectangle(
        [padding, height - padding - height // 6, width - padding, height - padding],
        outline="#ffaa00",
        width=3,
    )

    # Labels
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=max(14, width // 40))
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=max(10, width // 60))
    except OSError:
        font = ImageFont.load_default()
        font_small = font

    # Center text
    center_text = f"{width}x{height} | padding={padding}px"
    bbox = draw.textbbox((0, 0), center_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((width - tw) // 2, (height - th) // 2),
        center_text,
        fill="#ffffff",
        font=font,
    )

    # Zone labels
    draw.text((padding + 5, padding + 5), "TITLE ZONE", fill="#ffaa00", font=font_small)
    draw.text(
        (padding + 5, height - padding - height // 6 + 5),
        "FOOTER ZONE",
        fill="#ffaa00",
        font=font_small,
    )

    # Safe zone label
    draw.text((padding + 5, padding + height // 4 + 10), "RED = safe zone boundary", fill="#ff4444", font=font_small)

    # Fake "AI hallucinated text" in the middle to simulate the real problem
    fake_texts = [
        ("T-REX RRAPENS", (width // 4, height // 3)),
        ("JUDURAIR BAINHT", (width // 3, height * 2 // 3)),
        ("Prarrey CHILDREN", (width // 5, height // 2)),
    ]
    for text, pos in fake_texts:
        draw.text(pos, text, fill="#ffffff88", font=font)

    return img


def verify_overlay(
    theme_id: str,
    cover_path: str | None = None,
    output_path: str | None = None,
    width: int = 1024,
    height: int = 1024,
) -> Path:
    """Composite overlays onto a cover and save the result for visual inspection."""
    themes_dir = PROJECT_ROOT / "config" / "branding" / "themes"
    theme_file = themes_dir / f"{theme_id}.yml"

    if not theme_file.exists():
        available = [f.stem for f in themes_dir.glob("*.yml")]
        print(f"Theme '{theme_id}' not found. Available: {', '.join(sorted(available))}")
        sys.exit(1)

    # Load theme to get overlay paths
    import yaml

    with theme_file.open() as f:
        theme_data = yaml.safe_load(f)

    title_path = theme_data.get("cover_title_image", "")
    footer_path = theme_data.get("cover_footer_image", "")

    print(f"Theme:  {theme_id}")
    print(f"Title:  {title_path} (exists: {Path(title_path).exists() if title_path else 'N/A'})")
    print(f"Footer: {footer_path} (exists: {Path(footer_path).exists() if footer_path else 'N/A'})")
    print(f"Cover:  {cover_path or f'generated placeholder {width}x{height}'}")
    print(f'Padding: {PADDING_PX}px (safe_zone={KDP_SAFE_ZONE_INCHES}" + bleed={KDP_BLEED_INCHES}" @ {COVER_DPI} DPI)')
    print()

    # Load or create base cover
    if cover_path:
        base = Image.open(cover_path)
        width, height = base.size
    else:
        base = _create_test_cover(width, height)

    # Save base as bytes
    import io

    buf = io.BytesIO()
    base.save(buf, format="PNG")
    cover_bytes = buf.getvalue()

    # Apply compositor
    compositor = CoverCompositor()
    result_bytes = compositor.compose_cover(
        base_cover=cover_bytes,
        title_image_path=title_path,
        footer_image_path=footer_path,
    )

    # Load result and add debug annotations
    result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(result)

    try:
        font_debug = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=max(10, width // 60))
    except OSError:
        font_debug = ImageFont.load_default()

    # Draw safe zone boundary on result
    draw.rectangle(
        [PADDING_PX, PADDING_PX, width - PADDING_PX, height - PADDING_PX],
        outline="#ff000088",
        width=1,
    )

    # Annotate overlay positions
    if title_path and Path(title_path).exists():
        title_img = Image.open(title_path)
        tw, th = title_img.size
        # Scale down if needed
        max_w = width - 2 * PADDING_PX
        if tw > max_w:
            ratio = max_w / tw
            tw, th = max_w, int(th * ratio)
        tx = (width - tw) // 2
        ty = PADDING_PX
        draw.rectangle([tx, ty, tx + tw, ty + th], outline="#00ff00", width=2)
        draw.text((tx + 3, ty + th + 3), f"title: ({tx},{ty}) {tw}x{th}", fill="#00ff00", font=font_debug)

    if footer_path and Path(footer_path).exists():
        footer_img = Image.open(footer_path)
        fw, fh = footer_img.size
        max_w = width - 2 * PADDING_PX
        if fw > max_w:
            ratio = max_w / fw
            fw, fh = max_w, int(fh * ratio)
        fx = (width - fw) // 2
        fy = height - PADDING_PX - fh
        draw.rectangle([fx, fy, fx + fw, fy + fh], outline="#00ff00", width=2)
        draw.text((fx + 3, fy - 15), f"footer: ({fx},{fy}) {fw}x{fh}", fill="#00ff00", font=font_debug)

    # Save
    if output_path is None:
        output_path = f"cover_overlay_test_{theme_id}.png"
    out = Path(output_path)
    result.convert("RGB").save(out, format="PNG")

    print(f"Result saved to: {out.resolve()}")
    print(f"Image size: {width}x{height}")
    print()

    # Print position summary
    print("Overlay positions:")
    if title_path and Path(title_path).exists():
        title_img = Image.open(title_path)
        tw, th = title_img.size
        max_w = width - 2 * PADDING_PX
        if tw > max_w:
            ratio = max_w / tw
            tw, th = max_w, int(th * ratio)
        tx = (width - tw) // 2
        print(f"  Title:  x={tx}, y={PADDING_PX} (top edge + {PADDING_PX}px padding)")
        print(f"          size={tw}x{th}, covers top {((PADDING_PX + th) / height * 100):.1f}% of image")

    if footer_path and Path(footer_path).exists():
        footer_img = Image.open(footer_path)
        fw, fh = footer_img.size
        max_w = width - 2 * PADDING_PX
        if fw > max_w:
            ratio = max_w / fw
            fw, fh = max_w, int(fh * ratio)
        fy = height - PADDING_PX - fh
        print(f"  Footer: x={(width - fw) // 2}, y={fy} (bottom edge - {PADDING_PX}px - {fh}px)")
        print(f"          size={fw}x{fh}, covers bottom {((height - fy) / height * 100):.1f}% of image")

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify cover overlay placement")
    parser.add_argument("--theme", "-t", required=True, help="Theme ID (e.g., dinosaurs, pirates)")
    parser.add_argument("--cover", "-c", help="Path to a real cover image (optional, generates placeholder if omitted)")
    parser.add_argument("--output", "-o", help="Output file path (default: cover_overlay_test_<theme>.png)")
    parser.add_argument("--width", type=int, default=1024, help="Placeholder width (default: 1024)")
    parser.add_argument("--height", type=int, default=1024, help="Placeholder height (default: 1024)")
    args = parser.parse_args()

    verify_overlay(
        theme_id=args.theme,
        cover_path=args.cover,
        output_path=args.output,
        width=args.width,
        height=args.height,
    )


if __name__ == "__main__":
    main()
