"""
Instagram Banner Generator service.

Renders currency price boards for Instagram Story (1080x1920) and Post (1080x1080)
by reusing the existing Telegram banner rendering pipeline and scaling the output.
"""
from __future__ import annotations

import io
import functools
from pathlib import Path
from typing import Iterable, Tuple

from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from price_publisher.services.image_renderer import RenderedPriceImage
from price_publisher.services.legacy_category_renderer import (
    supports_category as is_gbp_category,
    render_category_board,
)
from price_publisher.services.tether_renderer import (
    supports_tether_category as is_tether_category,
    render_tether_board,
)

STORY_SIZE = (1080, 1920)
POST_SIZE = (1080, 1080)

STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
FONT_ROOT = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts"))


@functools.lru_cache(maxsize=4)
def _load_branding_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("Kalameh.ttf", "Morabba.ttf"):
        path = FONT_ROOT / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _get_telegram_image(category, price_items, timestamp) -> RenderedPriceImage:
    """Render the standard Telegram board for a category."""
    if is_tether_category(category):
        return render_tether_board(
            category=category,
            price_items=price_items,
            timestamp=timestamp,
        )
    return render_category_board(
        category=category,
        price_items=price_items,
        timestamp=timestamp,
    )


def _telegram_image_to_pil(rendered: RenderedPriceImage) -> Image.Image:
    rendered.stream.seek(0)
    return Image.open(rendered.stream).convert("RGBA")


def _fit_to_canvas(source: Image.Image, canvas_size: tuple[int, int]) -> Image.Image:
    """
    Scale and centre-crop the source onto a canvas of the given size.
    Preserves the full width, crops top/bottom symmetrically if needed,
    or pads with dark background if the source is too short.
    """
    cw, ch = canvas_size
    sw, sh = source.size

    scale = cw / sw
    new_w = cw
    new_h = int(sh * scale)

    scaled = source.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGBA", canvas_size, (15, 15, 20, 255))

    if new_h >= ch:
        top = (new_h - ch) // 2
        cropped = scaled.crop((0, top, cw, top + ch))
        canvas.paste(cropped, (0, 0))
    else:
        y_offset = (ch - new_h) // 2
        canvas.paste(scaled, (0, y_offset))

    return canvas


def _add_branding_bar(image: Image.Image, bar_height: int = 80) -> Image.Image:
    """Add a slim branding bar at the bottom with the exchange name."""
    draw = ImageDraw.Draw(image)
    w, h = image.size

    draw.rectangle([(0, h - bar_height), (w, h)], fill=(15, 15, 20, 230))

    font = _load_branding_font(max(28, bar_height // 3))
    text = "Sarafi Pardis | sarafipardis.co.uk"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = h - bar_height + (bar_height - th) // 2
    draw.text((tx, ty), text, font=font, fill=(212, 175, 55, 255))

    return image


class InstagramBannerService:
    """Generates Instagram Story and Post banners from existing price data."""

    @staticmethod
    def render_story(
        category,
        price_items: Iterable[Tuple],
        timestamp=None,
    ) -> RenderedPriceImage:
        """Render a 1080x1920 Instagram Story banner."""
        ts = timestamp or timezone.now()
        rendered = _get_telegram_image(category, list(price_items), ts)
        source = _telegram_image_to_pil(rendered)

        story = _fit_to_canvas(source, STORY_SIZE)
        story = _add_branding_bar(story, bar_height=90)

        buf = io.BytesIO()
        buf.name = "instagram_story.png"
        story.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return RenderedPriceImage(stream=buf, width=STORY_SIZE[0], height=STORY_SIZE[1])

    @staticmethod
    def render_post(
        category,
        price_items: Iterable[Tuple],
        timestamp=None,
    ) -> RenderedPriceImage:
        """Render a 1080x1080 Instagram Post banner."""
        ts = timestamp or timezone.now()
        rendered = _get_telegram_image(category, list(price_items), ts)
        source = _telegram_image_to_pil(rendered)

        post = _fit_to_canvas(source, POST_SIZE)
        post = _add_branding_bar(post, bar_height=70)

        buf = io.BytesIO()
        buf.name = "instagram_post.png"
        post.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return RenderedPriceImage(stream=buf, width=POST_SIZE[0], height=POST_SIZE[1])
