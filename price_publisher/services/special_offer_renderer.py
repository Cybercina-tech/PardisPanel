from __future__ import annotations

import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional, Sequence

import jdatetime
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from price_publisher.services.image_renderer import RenderedPriceImage

STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
IMAGE_ROOT = STATIC_ROOT_DIR / "img"
OFFER_ROOT = IMAGE_ROOT / "offer"
FONT_ROOT = Path(
    getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts")
)

OFFER_TEXT_POSITIONS = {
    "farsi_date": (1900, 250),
    "farsi_weekday": (1860, 420),
    "english_date": (420, 250),
    "english_weekday": (580, 420),
    "price": (360, 2100),
}

FONT_DEFINITIONS = {
    "farsi_date": ("Morabba.ttf", 115),
    "farsi_weekday": ("Morabba.ttf", 86),
    "english_date": ("YekanBakh.ttf", 100),
    "english_weekday": ("YekanBakh.ttf", 95),
    "english_number": ("montsrrat.otf", 115),
    "price": ("montsrrat.otf", 220),
}

FARSI_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}

FARSI_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def _normalize(value: str) -> str:
    return (
        (value or "")
        .strip()
        .replace("‌", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .lower()
    )


@dataclass(frozen=True)
class SpecialOfferTemplate:
    background: str
    aliases: set[str]


_SPECIAL_TEMPLATE_DEFINITIONS: Sequence[tuple[str, Iterable[str]]] = (
    (
        "offer1.png",
        (
            "خرید ویژه نقدی",
            "خریدویژهنقدی",
            "buycashspecial",
            "offer1",
        ),
    ),
    (
        "offer2.png",
        (
            "خرید ویژه از حساب",
            "خریدویژهازحساب",
            "buyaccountspecial",
            "offer2",
        ),
    ),
    (
        "offer3.png",
        (
            "خرید ویژه تتر",
            "خریدویژههتر",
            "buytether",
            "offer3",
        ),
    ),
    (
        "offer4.png",
        (
            "فروش ویژه نقدی",
            "فروشویژهنقدی",
            "sellcashspecial",
            "offer4",
        ),
    ),
    (
        "offer5.png",
        (
            "فروش ویژه از حساب",
            "فروشویژهازحساب",
            "sellaccountspecial",
            "offer5",
        ),
    ),
    (
        "offer6.png",
        (
            "فروش ویژه تتر",
            "فروشویژههتر",
            "selltether",
            "offer6",
        ),
    ),
)

SPECIAL_OFFER_TEMPLATES: tuple[SpecialOfferTemplate, ...] = tuple(
    SpecialOfferTemplate(
        background=background,
        aliases={_normalize(alias) for alias in aliases},
    )
    for background, aliases in _SPECIAL_TEMPLATE_DEFINITIONS
)


def supports_special_offer_type(special_price_type) -> bool:
    """Return True if the given special price type has a bespoke offer template."""
    return _resolve_template(special_price_type) is not None


def render_special_offer_board(
    *,
    special_price_type,
    price_history,
) -> RenderedPriceImage:
    """Render the pound special-offer board using branded templates."""
    template = _resolve_template(special_price_type)
    if not template:
        raise ValueError("No offer template configured for this special price type.")

    background_path = OFFER_ROOT / template.background
    if not background_path.exists():
        raise FileNotFoundError(
            f"Offer background missing at {background_path.relative_to(settings.BASE_DIR)}."
        )

    image = Image.open(background_path).convert("RGBA")
    draw_ctx = ImageDraw.Draw(image)
    fonts = _load_fonts()

    timestamp = _extract_timestamp(price_history)
    _draw_dates(draw_ctx, fonts, timestamp)

    price_text = _format_price_value(
        price_history, special_price_type=special_price_type
    )
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["price"],
        price_text,
        font=fonts["price"],
        fill=(0, 0, 0),
    )

    buffer = io.BytesIO()
    buffer.name = template.background
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


def _resolve_template(special_price_type) -> Optional[SpecialOfferTemplate]:
    identifiers = _collect_identifiers(special_price_type)
    if not identifiers:
        return None

    normalized = {_normalize(identifier) for identifier in identifiers}
    for template in SPECIAL_OFFER_TEMPLATES:
        if normalized & template.aliases:
            return template
    return None


def _collect_identifiers(special_price_type) -> set[str]:
    values = {
        getattr(special_price_type, "name", ""),
        getattr(special_price_type, "slug", ""),
        getattr(special_price_type, "description", ""),
    }
    return {value for value in values if value}


def _load_fonts():
    fonts = {}
    for key, (filename, size) in FONT_DEFINITIONS.items():
        font_path = FONT_ROOT / filename
        fonts[key] = ImageFont.truetype(str(font_path), size)
    return fonts


def _draw_dates(draw_ctx: ImageDraw.ImageDraw, fonts, timestamp):
    localized = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    jalali = jdatetime.datetime.fromgregorian(datetime=localized)
    farsi_date = _to_farsi_digits(
        f"{jalali.day} {_farsi_month(jalali.month)} {jalali.year}"
    )

    draw_ctx.text(
        OFFER_TEXT_POSITIONS["farsi_date"],
        farsi_date,
        font=fonts["farsi_date"],
        fill="white",
    )
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["farsi_weekday"],
        FARSI_WEEKDAYS.get(localized.strftime("%A"), ""),
        font=fonts["farsi_weekday"],
        fill="white",
    )

    english_date = localized.strftime("%Y %b %d")
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["english_date"],
        _to_english_digits(english_date),
        font=fonts["english_number"],
        fill="white",
    )
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["english_weekday"],
        localized.strftime("%A"),
        font=fonts["english_weekday"],
        fill="white",
    )


def _format_price_value(price_history, *, special_price_type=None) -> str:
    notes = (getattr(price_history, "notes", "") or "").strip().lower()
    if any(token in notes for token in ("call", "تماس")):
        return "تماس بگیرید"
    if any(token in notes for token in ("stop", "توقف")):
        trade_owner = special_price_type or getattr(
            price_history, "special_price_type", None
        )
        trade = getattr(trade_owner, "trade_type", "") or ""
        return "توقف خرید" if trade.lower() == "buy" else "توقف فروش"

    value = getattr(price_history, "price", None)
    if value is None:
        return "—"

    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, TypeError):
        return _to_english_digits(str(value))

    if decimal_value == decimal_value.to_integral():
        decimal_value = decimal_value.quantize(Decimal("1"))

    text = f"{decimal_value:,}"
    return _to_english_digits(text)


def _extract_timestamp(price_history):
    return getattr(price_history, "updated_at", None) or getattr(
        price_history, "created_at", None
    )


def _to_farsi_digits(value: str) -> str:
    return str(value).translate(FARSI_DIGITS)


def _to_english_digits(value: str) -> str:
    return str(value).translate(EN_DIGITS)


def _farsi_month(index: int) -> str:
    months = [
        "",
        "فروردین",
        "اردیبهشت",
        "خرداد",
        "تیر",
        "مرداد",
        "شهریور",
        "مهر",
        "آبان",
        "آذر",
        "دی",
        "بهمن",
        "اسفند",
    ]
    if 0 <= index < len(months):
        return months[index]
    return ""



