from __future__ import annotations

import io
import functools
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional, Tuple

import jdatetime
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from price_publisher.services.image_renderer import RenderedPriceImage

STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
IMAGE_ROOT = STATIC_ROOT_DIR / "img"
FONT_ROOT = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts"))
MEDIA_ROOT = Path(settings.MEDIA_ROOT)

# Tether banner background for EUR/AED/TRY + USDT/GBP rows
BACKGROUND_RELATIVE_PATH = Path("templates") / "tether_lir_derham_euro.jpg"
STATIC_FALLBACK_BACKGROUND = IMAGE_ROOT / "price_theme" / "tether_lir_derham_euro.jpg"


OFFER_TEXT_POSITIONS = {
    # Date fields
    "farsi_date": (2700, 200),
    "english_date": (280, 220),
    # Tether banner fields
    "tether_sell_eur": (1000, 730),   # یورو
    "tether_sell_aed": (1000, 1250),  # درهم
    "tether_sell_try": (1000, 1770),  # لیر
    "tether_buy_gbp": (1000, 2530),   # خرید تتر به پوند
    "tether_sell_gbp": (1000, 3050),  # فروش تتر به پوند
}

FONT_FILES = {
    "farsi_date": ("YekanBakhEN-Bold.ttf", 100),
    "english_date": ("YekanBakhEN-Bold.ttf", 100),
    "tether_price": ("YekanBakhEN-Bold.ttf", 200),
}

from core.formatting import (
    FARSI_WEEKDAYS,
    FARSI_DIGITS,
    EN_DIGITS,
    to_farsi_digits as _to_farsi_digits,
    to_english_digits as _to_english_digits,
    farsi_month as _farsi_month,
)

TETHER_LAYOUT_ORDER = [
    "tether_sell_eur",
    "tether_sell_aed",
    "tether_sell_try",
    "tether_buy_gbp",
    "tether_sell_gbp",
]


PRICE_TYPE_ALIASES = {
    "tether_buy_irr": {
        "tether_buy_irr",
        "tether-buy-irr",
        "buy_tether_irr",
        "buy-usdt-irr",
        "usdt_buy_irr",
        "tether_buy_toman",
        "buy_tether_toman",
        "buy_tether_tmn",
        "usdt_buy_tmn",
        "خرید_تتر_تومان",
        "خرید_تتر_تومن",
        "خریدتترتومن",
    },
    "tether_sell_irr": {
        "tether_sell_irr",
        "tether-sell-irr",
        "sell_tether_irr",
        "sell-usdt-irr",
        "usdt_sell_irr",
        "tether_sell_toman",
        "sell_tether_toman",
        "sell_tether_tmn",
        "usdt_sell_tmn",
        "فروش_تتر_تومان",
        "فروش_تتر_تومن",
        "فروشتترتومن",
    },
    "tether_buy_gbp": {
        "tether_buy_gbp",
        "tether-buy-gbp",
        "buy_tether_gbp",
        "buy-usdt-gbp",
        "usdt_buy_gbp",
        "buy_tether_pound",
        "buy_usdt_pound",
        "خرید_تتر_پوند",
        "خریدتترپوند",
    },
    "tether_sell_gbp": {
        "tether_sell_gbp",
        "tether-sell-gbp",
        "sell_tether_gbp",
        "sell-usdt-gbp",
        "usdt_sell_gbp",
        "sell_tether_pound",
        "sell_usdt_pound",
        "فروش_تتر_پوند",
        "فروشتترپوند",
    },
    "tether_sell_try": {
        "tether_sell_try",
        "tether_buy_try",
        "tether-sell-try",
        "tether-buy-try",
        "sell_tether_try",
        "buy_tether_try",
        "sell-usdt-try",
        "buy-usdt-try",
        "usdt_sell_try",
        "usdt_buy_try",
        "try",
        "lira",
        "لیر",
        "sell_tether_lira",
        "buy_tether_lira",
        "sell_usdt_lira",
        "buy_usdt_lira",
        "فروش_تتر_لیر",
        "خرید_تتر_لیر",
        "فروشتترلیر",
        "خریدتترلیر",
    },
    "tether_sell_aed": {
        "tether_sell_aed",
        "tether_buy_aed",
        "tether-sell-aed",
        "tether-buy-aed",
        "sell_tether_aed",
        "buy_tether_aed",
        "sell-usdt-aed",
        "buy-usdt-aed",
        "usdt_sell_aed",
        "usdt_buy_aed",
        "aed",
        "dirham",
        "درهم",
        "sell_tether_dirham",
        "buy_tether_dirham",
        "sell_usdt_dirham",
        "buy_usdt_dirham",
        "فروش_تتر_درهم",
        "خرید_تتر_درهم",
        "فروشتتردرهم",
        "خریدتتردرهم",
    },
    "tether_sell_eur": {
        "tether_sell_eur",
        "tether_buy_eur",
        "tether-sell-eur",
        "tether-buy-eur",
        "sell_tether_eur",
        "buy_tether_eur",
        "sell-usdt-eur",
        "buy-usdt-eur",
        "usdt_sell_eur",
        "usdt_buy_eur",
        "eur",
        "euro",
        "یورو",
        "sell_tether_euro",
        "buy_tether_euro",
        "sell_usdt_euro",
        "buy_usdt_euro",
        "فروش_تتر_یورو",
        "خرید_تتر_یورو",
        "فروشتتریورو",
        "خریدتتریورو",
    },
}


def supports_tether_category(category) -> bool:
    slug = (category.slug or "").lower()
    name = (category.name or "").lower()
    keywords = {
        "tether",
        "usdt",
        "تتر",
        "try",
        "lira",
        "لیر",
        "aed",
        "dirham",
        "درهم",
        "eur",
        "euro",
        "یورو",
    }
    return any(keyword in slug for keyword in keywords) or any(
        keyword in name for keyword in keywords
    )


def render_tether_board(
    *,
    category,
    price_items: Iterable[Tuple],
    timestamp,
) -> RenderedPriceImage:
    # Changed to use media/templates/USDT.jpg
    background_path = MEDIA_ROOT / BACKGROUND_RELATIVE_PATH
    if not background_path.exists():
        if STATIC_FALLBACK_BACKGROUND.exists():
            background_path = STATIC_FALLBACK_BACKGROUND
        else:
            raise FileNotFoundError(
                f"Tether offer background missing at {background_path} and static fallback {STATIC_FALLBACK_BACKGROUND}."
            )

    image = _open_background(background_path).copy()
    draw_ctx = ImageDraw.Draw(image)
    fonts = _load_fonts()

    # Draw Persian/English dates on tether board
    now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    _draw_tether_dates(draw_ctx, fonts, now)

    price_map = _build_price_map(price_items)
    for key in TETHER_LAYOUT_ORDER:
        entry = price_map.get(key)
        if not entry:
            continue

        draw_ctx.text(
            OFFER_TEXT_POSITIONS[key],
            entry,
            font=fonts["tether_price"],
            fill=(0, 0, 0),  # Completely black color
        )

    buffer = io.BytesIO()
    buffer.name = "tether_prices.png"
    image.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


@functools.lru_cache(maxsize=4)
def _open_background(path: Path) -> Image.Image:
    """Cache opened background images to avoid repeated disk I/O."""
    img = Image.open(path).convert("RGBA")
    img.load()
    return img


@functools.lru_cache(maxsize=1)
def _load_fonts():
    fonts = {}
    for key, (filename, size) in FONT_FILES.items():
        font_path = FONT_ROOT / filename
        if not font_path.exists():
            raise FileNotFoundError(
                f"Font file not found: {font_path}. "
                f"Please ensure the font file exists in the fonts directory."
            )
        try:
            fonts[key] = ImageFont.truetype(str(font_path), size)
        except OSError as e:
            if filename.endswith('.woff'):
                raise OSError(
                    f"Failed to load font '{filename}': PIL/Pillow does not support .woff files. "
                    f"Please provide a .ttf or .otf version of Kalameh font. "
                    f"Original error: {e}"
                ) from e
            raise
    return fonts


def _draw_tether_dates(draw_ctx: ImageDraw.ImageDraw, fonts, now):
    """Draw dates in required Persian and English formats."""
    weekday_en = now.strftime("%A")
    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    farsi_weekday = FARSI_WEEKDAYS.get(weekday_en, "")
    farsi_date_text = _to_farsi_digits(
        f"{farsi_weekday}, {jalali.day} {_farsi_month(jalali.month)} {jalali.year}"
    )
    english_date_text = f"{weekday_en}, {now.day} {now.strftime('%B')} {now.year}"

    draw_ctx.text(
        OFFER_TEXT_POSITIONS["farsi_date"],
        farsi_date_text,
        font=fonts["farsi_date"],
        fill=(0, 0, 0),
    )
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["english_date"],
        english_date_text,
        font=fonts["english_date"],
        fill=(0, 0, 0),
    )


def _draw_dates(draw_ctx: ImageDraw.ImageDraw, fonts, now):
    """Draw dates on tether board with correct timestamp and reshape for Persian text."""
    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    farsi_date = _to_farsi_digits(
        f"{jalali.day} {_farsi_month(jalali.month)} {jalali.year}"
    )
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["farsi_date"],
        farsi_date,
        font=fonts["farsi_date"],
        fill="white",
    )

    weekday_en = now.strftime("%A")
    farsi_weekday = FARSI_WEEKDAYS.get(weekday_en, "")
    
    # Use special position and font for Tuesday
    if weekday_en == "Tuesday":
        weekday_position = OFFER_TEXT_POSITIONS.get("farsi_weekday_tuesday", OFFER_TEXT_POSITIONS["farsi_weekday"])
        weekday_font = fonts.get("farsi_weekday_tuesday", fonts["farsi_weekday"])
    else:
        weekday_position = OFFER_TEXT_POSITIONS["farsi_weekday"]
        weekday_font = fonts["farsi_weekday"]
    
    draw_ctx.text(
        weekday_position,
        farsi_weekday,
        font=weekday_font,
        fill="white",
    )

    # English dates removed as requested - only Persian dates are shown


def _build_price_map(price_items: Iterable[Tuple]) -> dict:
    result: dict[str, str] = {}
    for price_type, price_history in price_items:
        key = _match_price_key(price_type)
        if not key:
            key = _fallback_match(price_type)
        if not key:
            continue
        result[key] = _format_history_value(price_history, key)
    return result


def _match_price_key(price_type) -> Optional[str]:
    identifiers = _collect_identifiers(price_type)
    for identifier in identifiers:
        normalized = _normalize(identifier)
        if not normalized:
            continue
        for key, aliases in PRICE_TYPE_ALIASES.items():
            if normalized in aliases:
                return key
    return None


def _fallback_match(price_type) -> Optional[str]:
    trade = (getattr(price_type, "trade_type", "") or "").lower()
    source = (getattr(price_type.source_currency, "code", "") or "").lower()
    target = (getattr(price_type.target_currency, "code", "") or "").lower()
    name = (getattr(price_type, "name", "") or "").lower()

    def _target_is_irr() -> bool:
        return any(
            token in target for token in ("irr", "irt", "rial", "toman")
        ) or any(token in name for token in ("تومان", "تومن"))

    def _target_is_gbp() -> bool:
        return "gbp" in target or "pound" in target or "پوند" in name

    def _target_is_try() -> bool:
        return "try" in target or "lira" in target or "لیر" in name

    def _target_is_aed() -> bool:
        return "aed" in target or "dirham" in target or "درهم" in name

    def _target_is_eur() -> bool:
        return "eur" in target or "euro" in target or "یورو" in name

    if _target_is_irr():
        if trade == "buy":
            return "tether_buy_irr"
        if trade == "sell":
            return "tether_sell_irr"
    if _target_is_gbp():
        if trade == "buy":
            return "tether_buy_gbp"
        if trade == "sell":
            return "tether_sell_gbp"
    if _target_is_try() and trade in {"buy", "sell"}:
        return "tether_sell_try"
    if _target_is_aed() and trade in {"buy", "sell"}:
        return "tether_sell_aed"
    if _target_is_eur() and trade in {"buy", "sell"}:
        return "tether_sell_eur"

    if trade == "buy":
        if "gbp" in name or "پوند" in name:
            return "tether_buy_gbp"
        return "tether_buy_irr"
    if trade == "sell":
        if "gbp" in name or "پوند" in name:
            return "tether_sell_gbp"
        if "try" in name or "lira" in name or "لیر" in name:
            return "tether_sell_try"
        if "aed" in name or "dirham" in name or "درهم" in name:
            return "tether_sell_aed"
        if "eur" in name or "euro" in name or "یورو" in name:
            return "tether_sell_eur"
        return "tether_sell_irr"

    return None


def _collect_identifiers(price_type) -> Tuple[str, ...]:
    slug = getattr(price_type, "slug", "") or ""
    name = getattr(price_type, "name", "") or ""
    trade = getattr(price_type, "trade_type", "") or ""
    source = getattr(price_type.source_currency, "code", "") or ""
    target = getattr(price_type.target_currency, "code", "") or ""

    combos = [
        slug,
        name,
        f"{name}_{trade}",
        f"{trade}_{name}",
        f"{trade}_{source}_{target}",
        f"{source}_{target}_{trade}",
        f"{name}_{source}_{target}_{trade}",
    ]
    return tuple(filter(None, combos))


def _normalize(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .lower()
    )


def _format_history_value(price_history, key: str) -> str:
    value = getattr(price_history, "price", None)

    # فقط عدد قیمت را نمایش می‌دهیم، هیچ متن دیگری نمایش داده نمی‌شود
    if value is None:
        return ""  # اگر قیمت وجود ندارد، خالی برمی‌گردانیم

    try:
        decimal_value = Decimal(value)
    except (InvalidOperation, TypeError):
        return ""  # اگر نمی‌توان قیمت را تبدیل کرد، خالی برمی‌گردانیم

    integral = decimal_value == decimal_value.to_integral()
    quantized = decimal_value.quantize(Decimal("1")) if integral else decimal_value
    text = f"{quantized:,}"
    return text  # فقط عدد قیمت با فرمت عددی




