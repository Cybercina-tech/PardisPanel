"""
Utility functions for rendering templates with dynamic data.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.utils.text import slugify
import os

logger = logging.getLogger(__name__)

# Default font candidates
DEFAULT_FONT_CANDIDATES = (
    getattr(settings, "TEMPLATE_EDITOR_DEFAULT_FONT", None),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "arial.ttf",
)


def _get_font(size: int, weight: str = 'normal') -> ImageFont.ImageFont:
    """Get font with specified size and weight."""
    for path in DEFAULT_FONT_CANDIDATES:
        if not path:
            continue
        try:
            font = ImageFont.truetype(path, size=size)
            # Note: PIL doesn't directly support font weight, but we can use different font files
            # For now, we'll use the same font regardless of weight
            return font
        except (OSError, IOError):
            continue
    logger.debug("Falling back to default bitmap font.")
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


def render_template(template_obj, dynamic_data_dict: Dict[str, Any]) -> Image.Image:
    """
    Render a template with dynamic data.
    
    Args:
        template_obj: Template model instance
        dynamic_data_dict: Dictionary with field names as keys and text values as values
                          Example: {'english_date': '2024-01-15', 'buy_price': '1,234.56'}
    
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
    config = template_obj.config.get('fields', {})
    
    # Draw each text field
    for field_name, field_config in config.items():
        # Get value from dynamic_data_dict, or use field name as fallback
        text_value = dynamic_data_dict.get(field_name, field_name)
        
        # Skip if text is empty
        if not str(text_value).strip():
            continue
        
        # Get field configuration
        x = field_config.get('x', 0)
        y = field_config.get('y', 0)
        size = field_config.get('size', 32)
        color = field_config.get('color', '#000000')
        align = field_config.get('align', 'left')
        max_width = field_config.get('max_width')
        weight = field_config.get('font_weight', 'normal')
        
        # Load font
        font = _get_font(size=size, weight=weight)
        
        # Parse color
        color_rgb = _parse_color(color)
        
        # Handle alignment
        if align == 'center' and max_width:
            # For center alignment with max_width, we need to calculate text width
            text_width = _measure_text(str(text_value), font, draw)
            if text_width < max_width:
                x = x + (max_width - text_width) // 2
        elif align == 'right' and max_width:
            text_width = _measure_text(str(text_value), font, draw)
            if text_width < max_width:
                x = x + max_width - text_width
        
        # Check if text is RTL
        direction = "rtl" if _is_rtl(str(text_value)) else None
        
        # Draw text with wrapping if max_width is specified
        if max_width:
            lines = _wrap_text(str(text_value), font, max_width, draw)
            try:
                line_height = font.getbbox("Ay")[3]
            except AttributeError:  # Pillow < 8.0 fallback
                line_height = font.getsize("Ay")[1]
            
            for i, line in enumerate(lines):
                line_y = y + i * (line_height + 4)
                
                # Draw shadow for readability
                shadow_offset = max(size // 18, 1)
                shadow_pos = (x + shadow_offset, line_y + shadow_offset)
                draw.text(
                    shadow_pos,
                    line,
                    font=font,
                    fill=(0, 0, 0, 192),
                    direction=direction,
                )
                
                # Draw main text with stroke
                stroke_width = max(size // 14, 1)
                draw.text(
                    (x, line_y),
                    line,
                    font=font,
                    fill=color_rgb,
                    stroke_width=stroke_width,
                    stroke_fill=(0, 0, 0),
                    direction=direction,
                )
        else:
            # Draw single line text
            shadow_offset = max(size // 18, 1)
            shadow_pos = (x + shadow_offset, y + shadow_offset)
            draw.text(
                shadow_pos,
                str(text_value),
                font=font,
                fill=(0, 0, 0, 192),
                direction=direction,
            )
            
            stroke_width = max(size // 14, 1)
            draw.text(
                (x, y),
                str(text_value),
                font=font,
                fill=color_rgb,
                stroke_width=stroke_width,
                stroke_fill=(0, 0, 0),
                direction=direction,
            )
    
    return base_image

