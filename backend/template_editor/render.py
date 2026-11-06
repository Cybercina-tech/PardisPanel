"""
Rendering of template-based price banners with themes and usage types.
Uses config.themes and config.usage_theme_map when present; falls back to config.fields.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from PIL import Image, ImageDraw

from .render_config_json import render_template_from_config_json
from .utils import (
    draw_text_field,
    render_template as legacy_render_template,
    _parse_color,
)
from .variables import get_default_sample_value

logger = logging.getLogger(__name__)

# Default base resolution for scaling (config can override with base_width, base_height)
DEFAULT_BASE_WIDTH = 1080
DEFAULT_BASE_HEIGHT = 1080


def _open_template_base_image(template_obj, config: Dict[str, Any], cj_raw: Dict[str, Any]) -> Image.Image:
    """Load template background file, or build a solid canvas (editor can be image-less)."""
    if getattr(template_obj, "image", None):
        try:
            bg_path = template_obj.image.path
            if Path(bg_path).is_file():
                return Image.open(bg_path).convert("RGBA")
        except Exception:
            logger.warning("template base image missing template_id=%s", getattr(template_obj, "pk", None))
    design_w = int(getattr(template_obj, "canvas_width", None) or DEFAULT_BASE_WIDTH)
    design_h = int(getattr(template_obj, "canvas_height", None) or DEFAULT_BASE_HEIGHT)
    if design_w < 1:
        design_w = DEFAULT_BASE_WIDTH
    if design_h < 1:
        design_h = DEFAULT_BASE_HEIGHT
    bg_hex = (
        (cj_raw or {}).get("backgroundColor")
        or (cj_raw or {}).get("background_color")
        or (config or {}).get("backgroundColor")
        or "#0b1220"
    )
    try:
        fill = _parse_color(bg_hex)
    except Exception:
        fill = (11, 18, 32, 255)
    return Image.new("RGBA", (design_w, design_h), fill)


def _scale_value(value: Any, scale: float) -> int:
    """Scale a numeric value by scale factor; return int."""
    if value is None:
        return None
    try:
        return int(round(float(value) * scale))
    except (TypeError, ValueError):
        return value


def _get_theme_name(config: Dict[str, Any], usage_type: str) -> str:
    """Resolve theme name from usage_theme_map or first theme in config."""
    usage_map = config.get("usage_theme_map") or {}
    if usage_type and usage_type in usage_map:
        return usage_map[usage_type]
    themes = config.get("themes") or {}
    if themes:
        return next(iter(themes))
    return None


def _get_layers_sorted(config: Dict[str, Any], theme_name: str) -> List[Dict[str, Any]]:
    """Get layers for theme, sorted by z_index then by order."""
    themes = config.get("themes") or {}
    theme = themes.get(theme_name) or {}
    layers = theme.get("layers") or []
    return sorted(
        layers,
        key=lambda L: (L.get("z_index", 0), layers.index(L) if L in layers else 0),
    )


def render_price_template(
    template_obj,
    usage_type: str,
    dynamic_data: Dict[str, Any],
    theme_name_override: str = None,
    config_override: Dict[str, Any] = None,
):
    """
    Render a template with usage-based theme selection and optional scaling.

    Config schema (when using themes):
      - base_width, base_height: optional; default 1080. Actual image size is scaled to this.
      - usage_theme_map: { usage_type: theme_name }
      - themes: { theme_name: { layers: [ { variable_key, x, y, font, size, color, align, max_width, z_index } ] } }

    If config has no ``themes`` but ``config_json.widgets`` is non-empty, renders those widgets
    onto the base image (same output size as the background). Otherwise falls back to
    legacy ``render_template`` (``config.fields``).

    theme_name_override: if provided, use this theme instead of resolving from usage_theme_map (e.g. for preview).
    config_override: if provided, use this config instead of template_obj.config (e.g. for live preview).

    Returns:
        PIL Image (RGBA).
    """
    config = config_override if config_override is not None else (template_obj.config or {})
    themes = config.get("themes")

    cj_raw = getattr(template_obj, "config_json", None) or {}
    if not isinstance(cj_raw, dict):
        cj_raw = {}
    widgets_list = cj_raw.get("widgets")

    if not themes and isinstance(widgets_list, list) and len(widgets_list) > 0:
        return render_template_from_config_json(template_obj, dynamic_data)

    if themes:
        theme_name = theme_name_override or _get_theme_name(config, usage_type)
        if not theme_name:
            if not template_obj.image:
                raise ValueError("Template has no image.")
            return legacy_render_template(template_obj, dynamic_data, config_override=config)

        layers = _get_layers_sorted(config, theme_name)
        if not layers:
            # Empty theme: just return background
            return _open_template_base_image(template_obj, config, cj_raw)

        base_image = _open_template_base_image(template_obj, config, cj_raw)
        draw = ImageDraw.Draw(base_image)
        actual_width, actual_height = base_image.size
        base_width = config.get("base_width") or getattr(
            template_obj, "canvas_width", None
        ) or DEFAULT_BASE_WIDTH
        base_height = config.get("base_height") or getattr(
            template_obj, "canvas_height", None
        ) or DEFAULT_BASE_HEIGHT
        scale_x = actual_width / float(base_width) if base_width else 1.0
        scale_y = actual_height / float(base_height) if base_height else 1.0

        for layer in layers:
            variable_key = layer.get("variable_key") or layer.get("key")
            if not variable_key:
                continue
            text_value = dynamic_data.get(variable_key)
            if text_value is None:
                text_value = get_default_sample_value(variable_key)
            text_value = str(text_value).strip()
            if not text_value:
                continue

            x = _scale_value(layer.get("x", 0), scale_x)
            y = _scale_value(layer.get("y", 0), scale_y)
            size = _scale_value(layer.get("size", 32), min(scale_x, scale_y))
            if size is None or size < 1:
                size = 32
            max_width = _scale_value(layer.get("max_width"), scale_x)
            color = layer.get("color", "#000000")
            align = layer.get("align", "left")
            font_filename = layer.get("font")

            draw_text_field(
                draw,
                x,
                y,
                text_value,
                size=size,
                color=color,
                align=align,
                max_width=max_width,
                font_filename=font_filename,
            )

        return base_image

    if not template_obj.image:
        raise ValueError("Template has no image.")
    bg_path = template_obj.image.path
    if not Path(bg_path).exists():
        raise FileNotFoundError(f"Template image not found at '{bg_path}'.")
    return legacy_render_template(template_obj, dynamic_data, config_override=config)
