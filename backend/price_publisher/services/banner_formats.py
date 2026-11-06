"""Size variants of a rendered price board for download.

``standard`` is the board exactly as published. ``story`` and ``post`` place the
whole board on an Instagram-sized canvas: nothing is cropped, the empty area is
filled with a dark, blurred copy of the board, and a handle footer is added.
"""
from __future__ import annotations

import io
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFilter, ImageFont

STANDARD = "standard"
STORY = "story"
POST = "post"

FORMAT_SIZES = {
    STANDARD: None,
    STORY: (1080, 1920),
    POST: (1080, 1080),
}
FORMATS = tuple(FORMAT_SIZES)

CANVAS_INSET = 32
FILL_COLOR = (13, 13, 13)
FOOTER_HEIGHT = 60
FOOTER_FILL = (20, 20, 20)
HANDLE_COLOR = (212, 175, 55)
DEFAULT_HANDLE = "@sarafipardis"


def is_valid_format(fmt: str) -> bool:
    return fmt in FORMAT_SIZES


def _handle_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_root = Path(
        getattr(settings, "PRICE_RENDERER_FONT_ROOT", Path(settings.BASE_DIR) / "static" / "fonts")
    )
    try:
        return ImageFont.truetype(str(font_root / "Kalameh.ttf"), 28)
    except OSError:
        return ImageFont.load_default()


def _fit_to_canvas(source: Image.Image, canvas_w: int, canvas_h: int) -> Image.Image:
    src_w, src_h = source.size
    inner_w = max(1, canvas_w - 2 * CANVAS_INSET)
    inner_h = max(1, canvas_h - 2 * CANVAS_INSET - FOOTER_HEIGHT)

    scale = min(inner_w / src_w, inner_h / src_h)
    scaled = source.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (canvas_w, canvas_h), FILL_COLOR)
    backdrop = source.resize((inner_w, inner_h), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(radius=40))
    shade = Image.new("RGBA", (inner_w, inner_h), (0, 0, 0, 180))
    backdrop = Image.alpha_composite(backdrop.convert("RGBA"), shade).convert("RGB")
    canvas.paste(backdrop, (CANVAS_INSET, CANVAS_INSET))
    canvas.paste(
        scaled,
        (
            CANVAS_INSET + (inner_w - scaled.width) // 2,
            CANVAS_INSET + (inner_h - scaled.height) // 2,
        ),
    )
    return canvas


def _add_footer(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    draw.rectangle([(0, h - FOOTER_HEIGHT), (w, h)], fill=FOOTER_FILL)
    text = getattr(settings, "BANNER_HANDLE", DEFAULT_HANDLE)
    font = _handle_font()
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((w - (right - left)) // 2 - left, h - FOOTER_HEIGHT + (FOOTER_HEIGHT - (bottom - top)) // 2 - top),
        text,
        font=font,
        fill=HANDLE_COLOR,
    )
    return img


def apply_format(png_bytes: bytes, fmt: str) -> bytes:
    """Return ``png_bytes`` resized to ``fmt``; ``standard`` returns it unchanged."""
    if fmt not in FORMAT_SIZES:
        raise ValueError(f"Unknown banner format: {fmt!r}")
    size = FORMAT_SIZES[fmt]
    if size is None:
        return png_bytes
    with Image.open(io.BytesIO(png_bytes)) as source:
        canvas = _add_footer(_fit_to_canvas(source.convert("RGB"), *size))
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()
