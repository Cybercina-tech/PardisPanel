import base64
import io
import logging
import os
from pathlib import Path
from typing import Iterable, List, Tuple, TypedDict

from django.conf import settings
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from .models import Element, Template

logger = logging.getLogger(__name__)


DEFAULT_FONT_CANDIDATES = (
    getattr(settings, "TEMPLATE_EDITOR_DEFAULT_FONT", None),
    # Common fonts on Linux and Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "arial.ttf",
)


def _is_rtl(text: str) -> bool:
    for char in text:
        if "\u0600" <= char <= "\u06FF" or "\u0750" <= char <= "\u077F":
            return True
    return False


def _get_font(size: int) -> ImageFont.ImageFont:
    for path in DEFAULT_FONT_CANDIDATES:
        if not path:
            continue
        try:
            return ImageFont.truetype(path, size=size)
        except (OSError, IOError):
            continue
    logger.debug("Falling back to default bitmap font.")
    return ImageFont.load_default()


def _measure_text(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> float:
    if hasattr(draw, "textlength"):
        return draw.textlength(text, font=font)
    if hasattr(font, "getlength"):
        return font.getlength(text)
    return font.getsize(text)[0]


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    if not text:
        return [""]

    words = text.split()
    if not words:
        return [text]

    lines: List[str] = []
    current_line = words[0]

    for word in words[1:]:
        trial_line = f"{current_line} {word}"
        width = _measure_text(trial_line, font, draw)
        if width <= max_width:
            current_line = trial_line
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines


def _parse_color(color: str) -> Tuple[int, int, int]:
    if not color:
        return 255, 255, 255
    color = color.strip()
    if color.startswith("#"):
        color = color[1:]
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    try:
        return tuple(int(color[i : i + 2], 16) for i in range(0, 6, 2))  # type: ignore[return-value]
    except ValueError:
        logger.warning("Invalid color value '%s', defaulting to white.", color)
        return 255, 255, 255


def _load_overlay(content: str) -> Image.Image:
    if not content:
        raise ValueError("Empty image content.")

    if content.startswith("data:"):
        header, encoded = content.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        return Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    potential_path = Path(content)
    if potential_path.is_file():
        return Image.open(potential_path).convert("RGBA")

    media_path = Path(settings.MEDIA_ROOT) / content
    if media_path.is_file():
        return Image.open(media_path).convert("RGBA")

    static_path = Path(settings.STATIC_ROOT or "") / content
    if static_path.is_file():
        return Image.open(static_path).convert("RGBA")

    raise FileNotFoundError(f"Unable to locate overlay image for content '{content}'.")


def _draw_text(draw: ImageDraw.ImageDraw, element: Element, canvas_size: Tuple[int, int]):
    content = element.content or ""
    if not content.strip():
        logger.debug("Skipping empty text element (ID: %s).", element.pk)
        return

    font = _get_font(size=max(element.font_size or 16, 8))
    color = _parse_color(element.color)
    width, height = canvas_size

    x = int((element.x or 0) / 100.0 * width)
    y = int((element.y or 0) / 100.0 * height)
    max_width = max(width - x - 20, width // 3)

    lines = _wrap_text(content, font, max_width, draw)
    try:
        line_height = font.getbbox("Ay")[3]
    except AttributeError:  # Pillow < 8.0 fallback
        line_height = font.getsize("Ay")[1]
    direction = "rtl" if _is_rtl(content) else None

    shadow_offset = max(font.size // 18, 1)
    stroke_width = max(font.size // 14, 1)

    for index, line in enumerate(lines):
        line_y = y + index * (line_height + 4)
        line_position = (x, line_y)
        # Draw soft shadow for readability
        shadow_pos = (line_position[0] + shadow_offset, line_position[1] + shadow_offset)
        draw.text(
            shadow_pos,
            line,
            font=font,
            fill=(0, 0, 0, 192),
            direction=direction,
        )
        draw.text(
            line_position,
            line,
            font=font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0),
            direction=direction,
        )


def _paste_overlay(image: Image.Image, element: Element, canvas_size: Tuple[int, int]):
    content = (element.content or "").strip()
    if not content:
        logger.debug("Skipping empty image element (ID: %s).", element.pk)
        return

    overlay = _load_overlay(content)
    width, height = canvas_size
    x = int((element.x or 0) / 100.0 * width)
    y = int((element.y or 0) / 100.0 * height)

    # Optional scaling based on font_size or additional metadata
    scale = max(element.font_size or 100, 24) / 100
    new_size = (
        max(1, int(overlay.width * scale)),
        max(1, int(overlay.height * scale)),
    )
    overlay = overlay.resize(new_size, Image.LANCZOS)

    image.alpha_composite(overlay, (x, y))


class RenderResult(TypedDict):
    url: str
    path: str


def _apply_watermark(image: Image.Image):
    logo_path = getattr(settings, "TEMPLATE_EDITOR_WATERMARK", None)
    if not logo_path:
        return
    try:
        watermark = _load_overlay(str(logo_path))
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.warning("Unable to load watermark '%s': %s", logo_path, exc)
        return

    scale_ratio = 0.12
    new_width = int(image.width * scale_ratio)
    resized_height = int(watermark.height * (new_width / watermark.width))
    watermark = watermark.resize((new_width, resized_height), Image.LANCZOS)

    margin = 24
    position = (image.width - watermark.width - margin, image.height - watermark.height - margin)
    image.alpha_composite(watermark, position)


def render_template(template: Template) -> str:
    if not template.background:
        raise ValueError("Template has no background image.")

    background_path = Path(template.background.path)
    if not background_path.exists():
        raise FileNotFoundError(f"Background image not found at '{background_path}'.")

    logger.info("Rendering template '%s' using background '%s'.", template, background_path)

    with Image.open(background_path).convert("RGBA") as base_image:
        draw = ImageDraw.Draw(base_image)
        canvas_size = base_image.size

        elements: Iterable[Element] = template.elements.all().order_by("id")
        for element in elements:
            try:
                if element.type == Element.ElementType.TEXT:
                    _draw_text(draw, element, canvas_size)
                elif element.type == Element.ElementType.IMAGE:
                    _paste_overlay(base_image, element, canvas_size)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Failed to render element %s: %s", element.pk, exc)

        _apply_watermark(base_image)

        output_dir = Path(settings.MEDIA_ROOT) / "rendered"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{slugify(template.name) or 'template'}-{template.pk}-{os.urandom(4).hex()}.png"
        output_path = output_dir / filename
        base_image.convert("RGB").save(output_path, format="PNG", optimize=True)

    relative_url = f"{settings.MEDIA_URL.rstrip('/')}/rendered/{filename}"
    logger.info("Rendered template '%s' stored at '%s'.", template, output_path)
    return RenderResult(url=relative_url, path=str(output_path))

