"""
PixelCast-style widget sync: map Template.config_json.widgets to Layer + Widget rows.

Also exposes _parse_position for percentage-based coordinates relative to canvas size.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from django.db import transaction

logger = logging.getLogger(__name__)


def _parse_position(value: Any, dimension: int) -> int:
    """
    Convert a stored coordinate (number or percentage string like "12.5%") to pixels
    for the given canvas dimension (width or height).
    """
    if value is None or dimension <= 0:
        return 0
    if isinstance(value, (int, float)):
        return int(round(float(value)))
    s = str(value).strip().replace("%", "")
    try:
        return int(round(float(s) / 100.0 * float(dimension)))
    except (TypeError, ValueError):
        return 0


def _normalize_widget_uuid(raw_id: Any) -> tuple[uuid.UUID, bool]:
    """
    Return (uuid_obj, changed) where changed is True if raw_id was not a valid UUID
    (caller should rewrite config_json with the new id).
    """
    if raw_id is None:
        return uuid.uuid4(), True
    try:
        return uuid.UUID(str(raw_id)), False
    except (ValueError, TypeError, AttributeError):
        return uuid.uuid4(), True


def _default_layer_for_template(template):
    from .models import Layer

    w = getattr(template, "canvas_width", None) or 1920
    h = getattr(template, "canvas_height", None) or 1080
    layer, _ = Layer.objects.get_or_create(
        template=template,
        name="Default Layer",
        defaults={"order": 0, "width": w, "height": h},
    )
    update = {}
    if layer.width != w:
        update["width"] = w
    if layer.height != h:
        update["height"] = h
    if update:
        Layer.objects.filter(pk=layer.pk).update(**update)
    return layer


def _content_url_for_widget(widget_type: str, content: Any) -> str:
    if not isinstance(content, str):
        return ""
    c = content.strip()
    if not c:
        return ""
    if widget_type in ("image", "video", "webview") and (
        c.startswith("http://") or c.startswith("https://")
    ):
        return c[:2000]
    return ""


def _sync_widgets_from_config(template, user=None) -> None:
    """
    Persist widgets from template.config_json into Layer + Widget rows.
    Rewrites unstable client ids in template.config_json when needed.
    """
    from .models import Widget, TemplateWidgetBinding

    raw = template.config_json if isinstance(template.config_json, dict) else {}
    widgets_data = raw.get("widgets")
    if not isinstance(widgets_data, list):
        return

    layer = _default_layer_for_template(template)
    seen: set[uuid.UUID] = set()
    config_changed = False

    with transaction.atomic():
        for w in widgets_data:
            if not isinstance(w, dict):
                continue
            wid, changed = _normalize_widget_uuid(w.get("id"))
            if changed:
                w["id"] = str(wid)
                config_changed = True

            wtype = (w.get("type") or "text").strip()[:40] or "text"
            style = w.get("style") if isinstance(w.get("style"), dict) else {}
            content = w.get("content", "")
            if not isinstance(content, str):
                content = str(content) if content is not None else ""

            content_url = _content_url_for_widget(wtype, content)

            def _pct(val: Any) -> str:
                if val is None:
                    return ""
                if isinstance(val, (int, float)):
                    return f"{float(val)}%"
                s = str(val).strip()
                return s if s else ""

            defaults = {
                "type": wtype,
                "name": (w.get("name") or "")[:200],
                "content": content[:10000],
                "content_url": content_url,
                "content_json": style,
                "z_index": int(w.get("zIndex", 0) or 0),
                "rotation": float(w.get("rotation", 0) or 0),
                "is_active": bool(w.get("visible", True)),
                "x_pct": _pct(w.get("x")),
                "y_pct": _pct(w.get("y")),
                "w_pct": _pct(w.get("width")),
                "h_pct": _pct(w.get("height")),
            }

            Widget.objects.update_or_create(
                widget_uuid=wid,
                defaults={**defaults, "layer": layer},
            )
            style = style if isinstance(style, dict) else {}
            raw_price_type_id = style.get("priceTypeId") or style.get("price_type_id")
            if raw_price_type_id not in (None, ""):
                try:
                    ptid = int(raw_price_type_id)
                except (TypeError, ValueError):
                    ptid = None
                if ptid is not None:
                    TemplateWidgetBinding.objects.update_or_create(
                        template=template,
                        widget_uuid=wid,
                        defaults={"price_type_id": ptid},
                    )
                else:
                    TemplateWidgetBinding.objects.filter(
                        template=template,
                        widget_uuid=wid,
                    ).delete()
            else:
                TemplateWidgetBinding.objects.filter(
                    template=template,
                    widget_uuid=wid,
                ).delete()
            seen.add(wid)

        Widget.objects.filter(layer=layer).exclude(widget_uuid__in=seen).delete()
        TemplateWidgetBinding.objects.filter(template=template).exclude(
            widget_uuid__in=seen
        ).delete()

    if config_changed:
        template.config_json = raw
        template.save(update_fields=["config_json", "updated_at"])


# Public alias used by views
sync_widgets_from_config = _sync_widgets_from_config
