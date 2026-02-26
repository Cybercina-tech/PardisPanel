"""
Service to generate Instagram-ready banners from existing Telegram price boards.
Produces Story (1080x1920) and Post (1080x1080) variants. The whole image always fits
(no cropping); any empty space is filled with a dark background; optional inset for spacing.
"""
from __future__ import annotations

import io
from typing import Iterable, Tuple

from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from price_publisher.services.image_renderer import RenderedPriceImage
from price_publisher.services.legacy_category_renderer import (
    render_category_board,
    supports_category,
)
from price_publisher.services.tether_renderer import (
    render_tether_board,
    supports_tether_category,
)

STORY_SIZE = (1080, 1920)
POST_SIZE = (1080, 1080)
# Inset from canvas edges so content has breathing room (more spacing)
CANVAS_INSET = 32
# Dark fill for empty areas (matches luxury black theme)
FILL_COLOR = (13, 13, 13)


def _render_board(category, price_items, timestamp) -> RenderedPriceImage:
    """Re-use the existing Telegram renderers to produce the raw board."""
    if supports_tether_category(category):
        return render_tether_board(
            category=category,
            price_items=price_items,
            timestamp=timestamp,
        )
    if supports_category(category):
        return render_category_board(
            category=category,
            price_items=price_items,
            timestamp=timestamp,
        )
    return render_category_board(
        category=category,
        price_items=price_items,
        timestamp=timestamp,
    )


def _fit_to_canvas(
    source: Image.Image,
    canvas_w: int,
    canvas_h: int,
    *,
    inset: int = CANVAS_INSET,
) -> Image.Image:
    """
    Place the entire source image onto a canvas of the requested size.
    The whole image always fits (no cropping). Uses an inset from edges for spacing.
    Any empty space is filled with a dark, solid background so the image looks complete.
    """
    src_w, src_h = source.size
    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS

    # Inner content area (with spacing from edges)
    inner_left = inset
    inner_top = inset
    inner_right = canvas_w - inset
    inner_bottom = canvas_h - inset
    inner_w = max(1, inner_right - inner_left)
    inner_h = max(1, inner_bottom - inner_top)

    # Scale so the entire image fits inside the inner area
    scale = min(inner_w / src_w, inner_h / src_h)
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    scaled = source.resize((new_w, new_h), resample)

    # Build canvas: dark fill everywhere so empty space is filled
    bg = Image.new("RGB", (canvas_w, canvas_h), FILL_COLOR)

    # Optional: subtle blurred background in content area for depth (keep fill visible at edges)
    blurred = source.resize((inner_w, inner_h), resample)
    blurred = blurred.filter(ImageFilter.GaussianBlur(radius=40))
    overlay = Image.new("RGBA", (inner_w, inner_h), (0, 0, 0, 180))
    blurred = blurred.convert("RGBA")
    blurred = Image.alpha_composite(blurred, overlay)
    blurred = blurred.convert("RGB")
    bg.paste(blurred, (inner_left, inner_top))

    # Center the scaled image in the inner area
    x_offset = inner_left + (inner_w - new_w) // 2
    y_offset = inner_top + (inner_h - new_h) // 2
    bg.paste(scaled, (x_offset, y_offset))

    return bg


def _add_branding(img: Image.Image, category_name: str) -> Image.Image:
    """Add a subtle branded footer bar at the bottom."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    bar_h = 60
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 180) if img.mode == "RGBA" else (20, 20, 20))

    try:
        from pathlib import Path
        from django.conf import settings
        font_root = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", Path(settings.BASE_DIR) / "static" / "fonts"))
        font_path = font_root / "Kalameh.ttf"
        font = ImageFont.truetype(str(font_path), 28)
    except Exception:
        font = ImageFont.load_default()

    text = f"@sarafiipardis"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((w - tw) // 2, h - bar_h + (bar_h - (bbox[3] - bbox[1])) // 2),
        text,
        font=font,
        fill=(212, 175, 55),
    )
    return img


def generate_story_banner(
    category,
    price_items: Iterable[Tuple],
    timestamp=None,
) -> io.BytesIO:
    """Generate a 1080x1920 Instagram Story banner and return a PNG BytesIO."""
    if timestamp is None:
        timestamp = timezone.now()
    board = _render_board(category, price_items, timestamp)
    board.stream.seek(0)
    source = Image.open(board.stream).convert("RGB")

    story = _fit_to_canvas(source, *STORY_SIZE)
    story = _add_branding(story, category.name)

    buf = io.BytesIO()
    buf.name = f"{category.slug or 'banner'}_story.png"
    story.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf


def generate_post_banner(
    category,
    price_items: Iterable[Tuple],
    timestamp=None,
) -> io.BytesIO:
    """Generate a 1080x1080 Instagram Post banner and return a PNG BytesIO."""
    if timestamp is None:
        timestamp = timezone.now()
    board = _render_board(category, price_items, timestamp)
    board.stream.seek(0)
    source = Image.open(board.stream).convert("RGB")

    post = _fit_to_canvas(source, *POST_SIZE)
    post = _add_branding(post, category.name)

    buf = io.BytesIO()
    buf.name = f"{category.slug or 'banner'}_post.png"
    post.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf
