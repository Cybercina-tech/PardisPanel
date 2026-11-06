"""
Utility functions for rendering templates with dynamic data.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from django.conf import settings

logger = logging.getLogger(__name__)

# Default font candidates - prioritize Persian fonts
STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
FONT_ROOT = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts"))

# Shipped OFL fonts (see scripts/download_template_fonts.ps1). Variable TTFs load with Pillow FreeType.
DEFAULT_RTL_FONT_FILENAME = "VazirmatnVF.ttf"
DEFAULT_LATIN_FONT_FILENAME = "InterVF.ttf"

# Explicit RTL-primary bundled files (latin-only content uses DEFAULT_LATIN_FONT_FILENAME instead).
BUNDLED_RTL_FONT_FILENAMES: frozenset[str] = frozenset(
    {
        DEFAULT_RTL_FONT_FILENAME,
        "vazir.ttf",
        "Kalameh.ttf",
        "YekanBakh.ttf",
        "Morabba.ttf",
    }
)

BUNDLED_LATIN_FONT_FILENAMES: frozenset[str] = frozenset(
    {
        DEFAULT_LATIN_FONT_FILENAME,
        "montsrrat.otf",
    }
)

_RTL_NAME_HINTS: tuple[str, ...] = (
    "vazir",
    "vazirmatn",
    "kalameh",
    "yekan",
    "morabba",
    "iran",
    "farsi",
    "nasim",
    "naskh",
    "notonaskh",
    "mehr",
    "samim",
    "shabnam",
    "tanha",
)

_LATIN_NAME_HINTS: tuple[str, ...] = (
    "inter",
    "montserrat",
    "roboto",
    "opensans",
    "lato",
    "arial",
    "helvetica",
    "dejavu",
    "freesans",
)


def _filename_hints_rtl(filename: str) -> bool:
    lower = (filename or "").lower()
    return any(h in lower for h in _RTL_NAME_HINTS)


def _filename_hints_latin(filename: str) -> bool:
    lower = (filename or "").lower()
    return any(h in lower for h in _LATIN_NAME_HINTS)


def font_script_hint(filename: str) -> str:
    """
    API metadata: primary script category for template editor font picker.
    unknown = uploaded/custom font — PIL does not substitute script fallback for these unless filename hints RTL.
    """
    base = Path(str(filename or "")).name
    if not base:
        return "unknown"
    if base in BUNDLED_LATIN_FONT_FILENAMES or _filename_hints_latin(base):
        return "ltr"
    if base in BUNDLED_RTL_FONT_FILENAMES or _filename_hints_rtl(base):
        return "both"
    return "unknown"


def resolve_font_filename_for_text(font_filename: Optional[str], text: Optional[str]) -> Optional[str]:
    """
    If a Persian-primary font is selected but the string has no Arabic-script characters,
    use the bundled Latin font so outlines stay readable (prices in Western digits, English labels).

    If a Latin-primary font is selected but the text contains Arabic script, use the bundled RTL font.
    """
    if not font_filename:
        return None
    base = Path(font_filename).name
    if text is None:
        return base
    s = str(text)
    if _is_rtl(s):
        if base in BUNDLED_LATIN_FONT_FILENAMES or (
            base not in BUNDLED_RTL_FONT_FILENAMES and _filename_hints_latin(base)
        ):
            return (
                DEFAULT_RTL_FONT_FILENAME if (FONT_ROOT / DEFAULT_RTL_FONT_FILENAME).is_file() else base
            )
        return base
    # Latin / digits / punctuation only — substitute away from RTL-primary faces if applicable.
    if base in BUNDLED_RTL_FONT_FILENAMES or (
        base not in BUNDLED_LATIN_FONT_FILENAMES and _filename_hints_rtl(base)
    ):
        return DEFAULT_LATIN_FONT_FILENAME if (FONT_ROOT / DEFAULT_LATIN_FONT_FILENAME).is_file() else base
    return base


class FontValidationError(ValueError):
    """An uploaded font file the renderer would not be able to use."""


# The four sfnt wrappers Pillow/FreeType can open. Checking the magic number
# first means a renamed archive is rejected as "not a font" rather than as some
# confusing parse error from deep inside FreeType.
_SFNT_MAGIC = (
    b"\x00\x01\x00\x00",  # TrueType
    b"OTTO",                 # CFF / OpenType
    b"true",                 # legacy Apple TrueType
    b"ttcf",                 # TrueType collection
)

FONT_EXTENSIONS = (".ttf", ".otf")


def validate_font_upload(uploaded, *, max_size: int) -> str:
    """Check an uploaded font is real and loadable; return its family name.

    The extension alone proves nothing — anything renamed to ``.ttf`` used to be
    written straight to disk, and only broke later as an unreadable ``@font-face``
    with no hint of why. Parsing it here turns that into an answer at upload time.

    :raises FontValidationError: with a message meant for the person uploading.
    """
    name = getattr(uploaded, "name", "") or ""
    extension = Path(name).suffix.lower()
    if extension not in FONT_EXTENSIONS:
        raise FontValidationError(
            "Only .ttf and .otf font files are supported. "
            "Convert a .woff or .woff2 to .ttf before uploading it."
        )

    size = getattr(uploaded, "size", 0) or 0
    if size <= 0:
        raise FontValidationError("That file is empty.")
    if size > max_size:
        raise FontValidationError(
            "That file is %d MB; the limit is %d MB."
            % (size // (1024 * 1024), max_size // (1024 * 1024))
        )

    try:
        uploaded.seek(0)
        head = uploaded.read(4)
        uploaded.seek(0)
    except Exception as exc:  # pragma: no cover - unreadable upload stream
        raise FontValidationError("The file could not be read.") from exc

    if head not in _SFNT_MAGIC:
        raise FontValidationError(
            "That file is not a TrueType or OpenType font. "
            "It may have been renamed, or saved in another format."
        )

    try:
        font = ImageFont.truetype(uploaded, size=16)
        family, _style = font.getname()
    except Exception as exc:
        logger.info("Rejected font upload %r: %s", name, exc)
        raise FontValidationError(
            "The font file is damaged or uses an unsupported variant, so it "
            "could not be loaded."
        ) from exc
    finally:
        try:
            uploaded.seek(0)
        except Exception:  # pragma: no cover - stream without seek
            pass

    return (family or Path(name).stem).strip()


def get_available_fonts() -> list[tuple[str, str]]:
    """
    Get list of available font files in the fonts directory.
    Returns list of tuples: (filename, display_name)
    Only returns .ttf and .otf files (PIL/Pillow compatible formats).
    """
    if not FONT_ROOT.exists():
        return []
    
    fonts = []
    for font_file in sorted(FONT_ROOT.glob("*")):
        if font_file.is_file() and font_file.suffix.lower() in ('.ttf', '.otf'):
            # Use filename without extension as display name
            display_name = font_file.stem
            fonts.append((font_file.name, display_name))
    
    return fonts


def _font_candidate_paths() -> Iterable[str]:
    """Existing files under FONT_ROOT first, then optional OS fonts."""
    yield getattr(settings, "TEMPLATE_EDITOR_DEFAULT_FONT", None)
    for name in (
        DEFAULT_RTL_FONT_FILENAME,
        DEFAULT_LATIN_FONT_FILENAME,
        "vazir.ttf",
        "Kalameh.ttf",
        "montsrrat.otf",
        "YekanBakh.ttf",
        "Morabba.ttf",
    ):
        p = FONT_ROOT / name
        if p.is_file():
            yield str(p)
    yield "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    yield "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    yield "arial.ttf"


def _get_font(
    size: int,
    weight: str = "normal",
    font_filename: Optional[str] = None,
    text: Optional[str] = None,
) -> ImageFont.ImageFont:
    """
    Get font with specified size and weight.

    Args:
        size: Font size in pixels
        weight: Font weight (not directly supported by PIL, kept for compatibility)
        font_filename: Optional font filename (e.g., 'InterVF.ttf').
        text: When set, may switch bundled RTL fonts to Latin for latin-only content.
    """
    resolved = resolve_font_filename_for_text(font_filename, text)

    if resolved:
        font_path = FONT_ROOT / resolved
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except (OSError, IOError) as e:
                logger.warning("Failed to load requested font '%s': %s. Falling back to default.", resolved, e)

    # Fall back to bundled / system candidates (only paths that exist)
    for path in _font_candidate_paths():
        if not path:
            continue
        try:
            if not Path(path).exists():
                continue
            font = ImageFont.truetype(path, size=size)
            return font
        except (OSError, IOError) as e:
            logger.debug("Failed to load font '%s': %s", path, e)
            continue
    logger.warning("Falling back to default bitmap font. Persian text may not display correctly.")
    return ImageFont.load_default()


def _parse_color(color_str: str) -> Tuple[int, int, int]:
    """Parse color string to RGB tuple."""
    if not color_str:
        return (0, 0, 0)
    color_str = color_str.strip()
    if color_str.startswith('#'):
        color_str = color_str[1:]
    if len(color_str) == 3:
        color_str = ''.join(c * 2 for c in color_str)
    try:
        return tuple(int(color_str[i:i+2], 16) for i in range(0, 6, 2))
    except ValueError:
        logger.warning(f"Invalid color value '{color_str}', defaulting to black.")
        return (0, 0, 0)


def _measure_text(text: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw) -> float:
    """Measure text width."""
    if hasattr(draw, "textlength"):
        return draw.textlength(text, font=font)
    if hasattr(font, "getlength"):
        return font.getlength(text)
    return font.getsize(text)[0]


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list:
    """Wrap text to fit within max_width."""
    if not text:
        return ['']
    
    words = text.split()
    if not words:
        return [text]
    
    lines = []
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


def _is_rtl(text: str) -> bool:
    """Check if text is right-to-left (Persian/Arabic)."""
    for char in text:
        if "\u0600" <= char <= "\u06FF" or "\u0750" <= char <= "\u077F":
            return True
    return False


def _shape_rtl_text_for_pil(text: str) -> str:
    """
    Reshape + bidi visual order for Pillow draw.text without libraqm RTL direction.
    """
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return text
    config = {
        "delete_harakat": True,
        "support_ligatures": True,
        "use_unshaped_instead_of_isolated": False,
    }
    reshaper = arabic_reshaper.ArabicReshaper(configuration=config)
    reshaped = reshaper.reshape(text)
    return get_display(reshaped)


def draw_text_field(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text_value: str,
    size: int = 32,
    color: str = "#000000",
    align: str = "left",
    max_width: int = None,
    font_filename: str = None,
    weight: str = "normal",
    stroke_width: Optional[int] = None,
    shadow: bool = True,
    use_arabic_reshape: bool = True,
) -> None:
    """
    Draw a single text field on the image (optional shadow + stroke).
    stroke_width=None keeps legacy auto stroke; 0 disables outline.
    When use_arabic_reshape and text contains Arabic script, applies arabic_reshaper + bidi
    and draws without Pillow direction=rtl (correct when libraqm is missing).
    """
    raw = str(text_value)
    font = _get_font(size=size, weight=weight, font_filename=font_filename, text=text_value)
    color_rgb = _parse_color(color)
    is_rtl_text = _is_rtl(raw)
    if use_arabic_reshape and is_rtl_text:
        text_to_draw = _shape_rtl_text_for_pil(raw)
        direction = None
    else:
        text_to_draw = raw
        direction = "rtl" if is_rtl_text else None

    if align == "center" and max_width:
        text_width = _measure_text(text_to_draw, font, draw)
        if text_width < max_width:
            x = x + (max_width - int(text_width)) // 2
    elif align == "right" and max_width:
        text_width = _measure_text(text_to_draw, font, draw)
        if text_width < max_width:
            x = x + max_width - int(text_width)
    if stroke_width is None:
        stroke_eff = max(size // 14, 1)
    else:
        stroke_eff = max(0, int(stroke_width))

    def _draw_one_line(px: int, py: int, line: str) -> None:
        def _safe_draw_text(position, *, fill, with_stroke=False):
            kwargs = {"font": font, "fill": fill}
            if with_stroke and stroke_eff > 0:
                kwargs["stroke_width"] = stroke_eff
                kwargs["stroke_fill"] = (0, 0, 0)
            if direction:
                kwargs["direction"] = direction
            try:
                draw.text(position, line, **kwargs)
            except KeyError as exc:
                # Pillow without libraqm cannot draw text with RTL direction.
                if "libraqm" not in str(exc).lower() or "direction" not in kwargs:
                    raise
                kwargs.pop("direction", None)
                draw.text(position, line, **kwargs)

        if shadow:
            shadow_offset = max(size // 18, 1)
            shadow_pos = (px + shadow_offset, py + shadow_offset)
            _safe_draw_text(shadow_pos, fill=(0, 0, 0, 192))
        if stroke_eff > 0:
            _safe_draw_text((px, py), fill=color_rgb, with_stroke=True)
        else:
            _safe_draw_text((px, py), fill=color_rgb)

    if max_width:
        lines = _wrap_text(text_to_draw, font, max_width, draw)
        try:
            line_height = font.getbbox("Ay")[3]
        except AttributeError:
            line_height = font.getsize("Ay")[1]
        for i, line in enumerate(lines):
            line_y = y + i * (line_height + 4)
            _draw_one_line(x, line_y, line)
    else:
        _draw_one_line(x, y, text_to_draw)


def render_template(template_obj, dynamic_data_dict: Dict[str, Any], config_override: Dict[str, Any] = None) -> Image.Image:
    """
    Render a template with dynamic data.

    Args:
        template_obj: Template model instance
        dynamic_data_dict: Dictionary with field names as keys and text values as values
                          Example: {'english_date': '2024-01-15', 'buy_price': '1,234.56'}
        config_override: Optional config dict to use instead of template_obj.config (e.g. for preview).

    Returns:
        PIL Image object with rendered template
    """
    if not template_obj.image:
        raise ValueError("Template has no image.")

    # Load template image
    bg_path = template_obj.image.path
    if not Path(bg_path).exists():
        raise FileNotFoundError(f"Template image not found at '{bg_path}'.")

    logger.info(f"Rendering template '{template_obj.name}' using image '{bg_path}'.")

    # Open and convert to RGBA
    base_image = Image.open(bg_path).convert('RGBA')
    draw = ImageDraw.Draw(base_image)
    canvas_size = base_image.size

    # Get configuration
    config = (config_override if config_override is not None else template_obj.config or {}).get('fields', {})
    
    # Draw each text field
    for field_name, field_config in config.items():
        # Get value from dynamic_data_dict, or use field name as fallback
        text_value = dynamic_data_dict.get(field_name, field_name)

        # Skip if text is empty
        if not str(text_value).strip():
            continue

        x = field_config.get('x', 0)
        y = field_config.get('y', 0)
        size = field_config.get('size', 32)
        color = field_config.get('color', '#000000')
        align = field_config.get('align', 'left')
        max_width = field_config.get('max_width')
        weight = field_config.get('font_weight', 'normal')
        font_filename = field_config.get('font')

        draw_text_field(
            draw, x, y, str(text_value),
            size=size, color=color, align=align, max_width=max_width,
            font_filename=font_filename, weight=weight,
        )

    return base_image

