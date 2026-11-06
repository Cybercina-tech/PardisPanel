"""
Render Template.config_json.widgets onto the base image (PIL).
Coordinates are percentage strings relative to logical canvas (canvas_width x canvas_height).
"""

from __future__ import annotations

import io
import logging
import re
from numbers import Real
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

from django.conf import settings
from PIL import Image, ImageDraw

from core.utils import format_price_display, to_persian_digits
from .utils import draw_text_field, _parse_color
from .variables import get_default_sample_value

logger = logging.getLogger(__name__)


def _looks_like_placeholder_text(value: Any) -> bool:
    s = str(value or "").strip()
    if not s:
        return True
    lowered = s.lower()
    if lowered in {"sample text", "text"}:
        return True
    if s.startswith("[") and s.endswith("]"):
        return True
    return False


_PRICE_KEY_EXACT = {"price"}
_PRICE_KEY_PREFIXES = (
    "price__",
    "price_type__",
    "price_buy__",
    "price_sell__",
    "price_buy_",
    "price_sell_",
    "tether_buy_",
    "tether_sell_",
)
_DIGIT_RE = re.compile(r"\d")
_ALPHA_RE = re.compile(r"[A-Za-z\u0600-\u06FF]")


def _is_price_like_key(key: str) -> bool:
    k = str(key or "").strip().lower()
    if not k:
        return False
    if k in _PRICE_KEY_EXACT:
        return True
    return k.startswith(_PRICE_KEY_PREFIXES)


def _is_probable_price_text(value: Any) -> bool:
    s = str(value or "").strip()
    if not s:
        return False
    # Price text must include digits and should not include letters/month names.
    if not _DIGIT_RE.search(s):
        return False
    if _ALPHA_RE.search(s):
        return False
    return True


def _fallback_price_text(dynamic_data: Dict[str, Any]) -> str:
    # Prefer any available live price token before hard fallback.
    for key, raw in (dynamic_data or {}).items():
        if not _is_price_like_key(str(key or "")):
            continue
        text = _format_widget_value(raw).strip()
        if text and _is_probable_price_text(text):
            return text
    return "123,456"


def _format_widget_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, Real):
        return format_price_display(value)
    if isinstance(value, str) and value.strip():
        return format_price_display(value)
    return str(value)


def _text_fx_from_style(style: Dict[str, Any]) -> tuple[str, Optional[int], bool]:
    """Resolve PIL text weight, stroke width, and shadow flag from widget style."""
    fw = style.get("fontWeight") or style.get("weight") or "normal"
    s = str(fw).strip().lower()
    weight = "bold" if s in ("bold", "700", "800", "900") else "normal"
    if style.get("plainText") is True or style.get("plain_text") is True:
        return weight, 0, False
    ts = style.get("textShadow")
    # Keep output readable by default: no shadow unless explicitly enabled.
    use_shadow = ts is True or str(ts).lower() == "true"
    sw = style.get("textStrokeWidth")
    if sw is not None:
        try:
            return weight, max(0, int(sw)), use_shadow
        except (TypeError, ValueError):
            pass
    # Keep output readable by default: no outline unless explicitly enabled.
    outline_enabled = style.get("textOutline") is True or style.get("text_outline") is True
    if outline_enabled:
        return weight, None, use_shadow
    return weight, 0, use_shadow


def _pct_to_fraction(raw: Any) -> float:
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw) / 100.0 if raw <= 100 else float(raw) / 100.0  # allow bare numbers as percent
    s = str(raw).strip().replace("%", "")
    try:
        return float(s) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _design_to_actual_font_scale(
    design_w: int,
    design_h: int,
    actual_w: int,
    actual_h: int,
) -> float:
    """
    Scale factor for style.fontSize (stored in template canvas px) when the background
    image pixel size differs from template.canvas_width / canvas_height.

    Widget boxes already scale via _logical_to_actual; fonts must use the same mapping.
    min(sx, sy) matches single-line box-fit behavior (limiting axis), matching the editor.
    """
    if design_w < 1 or design_h < 1:
        return 1.0
    sx = actual_w / float(design_w)
    sy = actual_h / float(design_h)
    return min(sx, sy)


def _logical_to_actual(
    raw: Any,
    design_size: int,
    actual_size: int,
) -> int:
    frac = _pct_to_fraction(raw)
    px_design = frac * float(design_size)
    if design_size <= 0:
        return 0
    scale = actual_size / float(design_size)
    return int(round(px_design * scale))


def _price_bind_fallback(binding: str, dynamic_data: Dict[str, Any], w: Dict[str, Any], *, treat_as_price: bool) -> str:
    """When primary dynamic key(s) missed, mirror legacy binding fallbacks."""
    fallback_content = w.get("content")
    if (
        fallback_content is not None
        and str(fallback_content).strip()
        and not _looks_like_placeholder_text(fallback_content)
    ):
        return str(fallback_content).strip()
    b = str(binding).strip().lower()
    if treat_as_price or (b and _is_price_like_key(b)):
        return _fallback_price_text(dynamic_data)
    if not b:
        return _fallback_price_text(dynamic_data) if treat_as_price else ""
    sample = get_default_sample_value(str(binding).strip())
    sample_text = _format_widget_value(sample).strip()
    if _looks_like_placeholder_text(sample_text):
        return _fallback_price_text(dynamic_data)
    return sample_text


def _price_locale_is_fa(style: Dict[str, Any]) -> bool:
    loc = str(style.get("priceLocale") or style.get("price_locale") or "en").strip().lower()
    return loc in ("fa", "fas", "persian")


def _widget_is_price_bound(w: Dict[str, Any]) -> bool:
    style = w.get("style") if isinstance(w.get("style"), dict) else {}
    raw_pt = style.get("priceTypeId")
    if raw_pt is None:
        raw_pt = style.get("price_type_id")
    if raw_pt not in (None, ""):
        return True
    binding_raw = (
        w.get("bindingKey")
        or w.get("binding_key")
        or style.get("bindingKey")
        or style.get("binding_key")
    )
    bk = str(binding_raw).strip() if binding_raw else ""
    return bool(bk and _is_price_like_key(bk))


def _apply_price_digit_locale(text: str, w: Dict[str, Any]) -> str:
    if not text or not text.strip():
        return text
    style = w.get("style") if isinstance(w.get("style"), dict) else {}
    if not _widget_is_price_bound(w) or not _price_locale_is_fa(style):
        return text
    if not _is_probable_price_text(text):
        return text
    return to_persian_digits(text)


def _widget_text_value(w: Dict[str, Any], dynamic_data: Dict[str, Any]) -> str:
    style = w.get("style") if isinstance(w.get("style"), dict) else {}
    binding_raw = (
        w.get("bindingKey")
        or w.get("binding_key")
        or style.get("bindingKey")
        or style.get("binding_key")
    )
    binding = str(binding_raw).strip() if binding_raw else ""
    wtype = (w.get("type") or "text").strip()

    raw_ptid = style.get("priceTypeId") or style.get("price_type_id")
    pt_key = None
    if raw_ptid not in (None, ""):
        try:
            pt_key = f"price_type__{int(raw_ptid)}"
        except (TypeError, ValueError):
            pt_key = None

    if pt_key:
        val = dynamic_data.get(pt_key)
        if val is not None and str(val).strip():
            return _format_widget_value(val).strip()
        if binding:
            val = dynamic_data.get(binding)
            if val is not None and str(val).strip():
                return _format_widget_value(val).strip()
        return _price_bind_fallback(binding, dynamic_data, w, treat_as_price=True)

    if binding:
        val = dynamic_data.get(binding)
        if val is not None and str(val).strip():
            return _format_widget_value(val).strip()
        return _price_bind_fallback(binding, dynamic_data, w, treat_as_price=False)
    if wtype in ("date", "weekday"):
        key = style.get("dateKey") or style.get("date_key") or "date_fa"
        return _format_widget_value(dynamic_data.get(key) or get_default_sample_value(key)).strip()
    if wtype == "clock":
        return _format_widget_value(dynamic_data.get("time") or get_default_sample_value("time")).strip()
    content = w.get("content", "")
    return str(content) if content is not None else ""


def _resolve_local_image_path(content: str) -> Optional[Path]:
    c = (content or "").strip()
    if not c:
        return None
    media_prefix = settings.MEDIA_URL.rstrip("/") if settings.MEDIA_URL else "/media"
    if c.startswith("/media/") or (media_prefix and c.startswith(media_prefix + "/")):
        prefix = "/media/" if c.startswith("/media/") else f"{media_prefix}/"
        rel = c[len(prefix) :].lstrip("/")
        p = Path(settings.MEDIA_ROOT) / rel
        return p if p.is_file() else None
    p = Path(c)
    if p.is_file():
        return p
    static_path = Path(settings.BASE_DIR) / "static" / c.lstrip("/")
    if static_path.is_file():
        return static_path
    return None


def _paste_scaled_image(
    base: Image.Image,
    box_xy,
    box_wh,
    src: Image.Image,
    opacity: float = 1.0,
) -> None:
    x0, y0 = box_xy
    bw, bh = box_wh
    if bw < 1 or bh < 1:
        return
    resized = src.resize((bw, bh), Image.Resampling.LANCZOS)
    if resized.mode != "RGBA":
        resized = resized.convert("RGBA")
    try:
        op = float(opacity)
    except (TypeError, ValueError):
        op = 1.0
    op = max(0.0, min(1.0, op))
    if op < 1.0 - 1e-6:
        r, g, b, a = resized.split()
        a = a.point(lambda p: int(round(p * op)))
        resized = Image.merge("RGBA", (r, g, b, a))
    base.paste(resized, (x0, y0), resized)


def render_template_from_config_json(
    template_obj,
    dynamic_data: Dict[str, Any],
    config_json_override: Optional[Dict[str, Any]] = None,
) -> Image.Image:
    """
    Draw widgets from config_json onto template_obj.image (required).
    Logical size: template canvas_width / canvas_height (defaults 1920x1080).
    Output size matches the background image dimensions.
    """
    raw = config_json_override if config_json_override is not None else (template_obj.config_json or {})
    if not isinstance(raw, dict):
        raw = {}
    widgets = raw.get("widgets")
    if not isinstance(widgets, list):
        widgets = []

    design_w = int(getattr(template_obj, "canvas_width", None) or 1920)
    design_h = int(getattr(template_obj, "canvas_height", None) or 1080)
    if design_w < 1:
        design_w = 1920
    if design_h < 1:
        design_h = 1080

    if getattr(template_obj, "image", None):
        bg_path = template_obj.image.path
        if Path(bg_path).is_file():
            base_image = Image.open(bg_path).convert("RGBA")
        else:
            bg_hex = (
                raw.get("backgroundColor")
                or raw.get("background_color")
                or "#0b1220"
            )
            try:
                fill = _parse_color(bg_hex)
            except Exception:
                fill = (11, 18, 32, 255)
            base_image = Image.new("RGBA", (design_w, design_h), fill)
    else:
        bg_hex = (
            raw.get("backgroundColor")
            or raw.get("background_color")
            or "#0b1220"
        )
        try:
            fill = _parse_color(bg_hex)
        except Exception:
            fill = (11, 18, 32, 255)
        base_image = Image.new("RGBA", (design_w, design_h), fill)

    actual_w, actual_h = base_image.size
    font_scale = _design_to_actual_font_scale(design_w, design_h, actual_w, actual_h)

    sorted_widgets: List[Dict[str, Any]] = sorted(
        [w for w in widgets if isinstance(w, dict)],
        key=lambda w: int(w.get("zIndex") or w.get("z_index") or 0),
    )
    draw = ImageDraw.Draw(base_image)

    for w in sorted_widgets:
        if w.get("visible") is False:
            continue
        wtype = (w.get("type") or "text").strip()
        x = _logical_to_actual(w.get("x"), design_w, actual_w)
        y = _logical_to_actual(w.get("y"), design_h, actual_h)
        ww = _logical_to_actual(w.get("width"), design_w, actual_w)
        hh = _logical_to_actual(w.get("height"), design_h, actual_h)
        if ww < 2 or hh < 2:
            continue
        style = w.get("style") if isinstance(w.get("style"), dict) else {}

        if wtype == "image":
            content = str(w.get("content") or "").strip()
            pth = _resolve_local_image_path(content)
            im_src = None
            if pth:
                try:
                    im_src = Image.open(pth).convert("RGBA")
                except OSError as e:
                    logger.warning("widget image load failed path=%s err=%s", pth, e)
            elif content.startswith(("http://", "https://")):
                try:
                    with urlopen(content, timeout=10) as resp:  # noqa: S310 — admin-controlled URL
                        im_src = Image.open(io.BytesIO(resp.read())).convert("RGBA")
                except Exception as e:
                    logger.warning("widget image url failed url=%s err=%s", content[:120], e)
            if im_src:
                try:
                    iop = float(style.get("opacity", 1))
                except (TypeError, ValueError):
                    iop = 1.0
                _paste_scaled_image(base_image, (x, y), (ww, hh), im_src, opacity=iop)
            continue

        if wtype == "price_board":
            continue

        text_val = _widget_text_value(w, dynamic_data)
        text_val = _apply_price_digit_locale(text_val, w)
        if not text_val.strip():
            continue
        try:
            raw_fs = int(style.get("fontSize") or style.get("font_size") or max(14, min(hh - 4, int(hh * 0.45))))
        except (TypeError, ValueError):
            raw_fs = max(14, min(hh - 4, int(hh * 0.45)))
        font_size = int(round(raw_fs * font_scale))
        # Fit inside widget box (editor single-line fit); removes old hard 200px cap.
        font_size = max(8, min(font_size, max(hh - 8, 8)))
        color = style.get("color") or "#ffffff"
        font_fn = style.get("font") or style.get("fontFilename") or style.get("font_filename")
        tw, tstroke, tshadow = _text_fx_from_style(style)
        use_arabic_reshape = style.get("useArabicReshaper", style.get("use_arabic_reshaper", True))
        if isinstance(use_arabic_reshape, str):
            use_arabic_reshape = use_arabic_reshape.strip().lower() in ("1", "true", "yes", "on")
        draw_text_field(
            draw,
            x + 4,
            y + 4,
            text_val,
            size=font_size,
            color=str(color),
            align=str(style.get("align") or "center"),
            max_width=max(8, ww - 8),
            font_filename=font_fn,
            weight=tw,
            stroke_width=tstroke,
            shadow=tshadow,
            use_arabic_reshape=bool(use_arabic_reshape),
        )

    return base_image
