"""
Build headless-render context payloads for Playwright screenshot pipeline.
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Iterable, Optional, Tuple

from django.core.files.storage import default_storage

from .font_face_tokens import sign_font_face_filename
from .render_config_json import _apply_price_digit_locale, _widget_text_value
from .utils import font_script_hint, get_available_fonts


def _template_image_url(template_obj) -> str:
    image = getattr(template_obj, "image", None)
    if not image:
        return ""
    name = getattr(image, "name", None)
    if not name:
        return ""
    try:
        if not default_storage.exists(name):
            return ""
    except Exception:
        return ""
    try:
        url = image.url
    except Exception:
        return ""
    if url.startswith(("http://", "https://")):
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.path.startswith("/media/"):
            return parsed.path
        return url
    return url if url.startswith("/") else f"/{url.lstrip('/')}"


def _build_price_binding_map(dynamic_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Map binding keys to preview-map entries consumed by Vue widgets."""
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(dynamic_data, dict):
        return result

    for key, raw_val in dynamic_data.items():
        key_str = str(key).strip()
        if not key_str:
            continue
        if not (
            key_str.startswith("price__")
            or key_str.startswith("price_type__")
            or key_str.startswith("price_buy__")
            or key_str.startswith("price_sell__")
            or key_str == "price"
        ):
            continue
        value = "" if raw_val is None else str(raw_val).strip()
        entry = {
            "value": value,
            "source": "publish",
            "has_value": bool(value),
            "label": key_str,
            "binding_key": key_str,
        }
        result[key_str] = entry
    return result


def resolve_widget_content(widget: Dict[str, Any], dynamic_data: Dict[str, Any]) -> str:
    """Resolve display text for a widget using publish-time dynamic_data."""
    text = _widget_text_value(widget, dynamic_data)
    return _apply_price_digit_locale(text, widget)


def _resolve_widgets(widgets: list, dynamic_data: Dict[str, Any]) -> list:
    resolved = []
    for raw in widgets or []:
        if not isinstance(raw, dict):
            continue
        w = copy.deepcopy(raw)
        content = resolve_widget_content(w, dynamic_data)
        if content:
            w["content"] = content
        resolved.append(w)
    return resolved


def _fonts_payload() -> list:
    return [
        {
            "filename": f[0],
            "display_name": f[1],
            "script": font_script_hint(f[0]),
            "face_token": sign_font_face_filename(f[0]),
        }
        for f in get_available_fonts()
    ]


def build_headless_context(
    template,
    dynamic_data: Dict[str, Any],
    price_items: Optional[Iterable[Tuple[Any, Any]]] = None,
) -> Dict[str, Any]:
    """
    Build Redis-stored context for the Vue headless render route.

    price_items is accepted for API symmetry with the screenshot engine; binding
    resolution uses dynamic_data produced at publish time.
    """
    del price_items  # reserved for future per-item overrides

    cj_raw = getattr(template, "config_json", None) or {}
    if not isinstance(cj_raw, dict):
        cj_raw = {}
    widgets = cj_raw.get("widgets") if isinstance(cj_raw.get("widgets"), list) else []

    return {
        "template_id": getattr(template, "pk", None),
        "category_id": getattr(template, "category_id", None),
        "canvas_width": int(getattr(template, "canvas_width", None) or 1080),
        "canvas_height": int(getattr(template, "canvas_height", None) or 1080),
        "background_color": cj_raw.get("backgroundColor")
        or cj_raw.get("background_color")
        or "#ffffff",
        "image_url": _template_image_url(template),
        "widgets": _resolve_widgets(widgets, dynamic_data or {}),
        "price_binding_map": _build_price_binding_map(dynamic_data or {}),
        "fonts": _fonts_payload(),
    }
