from __future__ import annotations

import io
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

# Changed to use USDT.jpg from media/templates/
BACKGROUND_RELATIVE_PATH = Path("templates") / "USDT.jpg"


OFFER_TEXT_POSITIONS = {
    # Date fields
    "farsi_date": (1900, 250),
    "farsi_weekday": (1860, 420),  # Default position
    "farsi_weekday_tuesday": (615, 435),  # Special position for Tuesday: x=615, y=435
    "english_date": (410, 250),  # Moved slightly to the left
    "english_weekday": (580, 420),
    # Tether banner date fields
    "tether_date": (1280, 300),  # Date format: "14 dec"
    "tether_year": (1305, 410),  # Year: "2025"
    # Updated coordinates for new banner
    "tether_sell_irr": (540, 1151),  # فروش تتر به تومن
    "tether_buy_irr": (1750, 1150),    # خرید تتر به تومن
    "tether_buy_gbp": (690, 1920),    # خرید تتر به پوند
    "tether_sell_gbp": (1860, 1920),   # فروش تتر به پوند
    "working_hours": (1200, 2200),   # ساعات کاری
}

FONT_FILES = {
    # Date fonts
    "farsi_date": ("Morabba.ttf", 200),
    "farsi_weekday": ("Morabba.ttf", 200),
    "farsi_weekday_tuesday": ("Morabba.ttf", 200),  # Size 200 for Tuesday
    "english_date": ("montsrrat.otf", 200),  # Changed to English font
    "english_weekday": ("montsrrat.otf", 200),  # Changed to English font
    "english_number": ("montsrrat.otf", 200),  # Size 200
    "tether_price": ("montsrrat.otf", 200),  # English font for Tether prices
    "working_hours": ("Morabba.ttf", 200),  # ساعات کاری
    # Tether banner date fonts (English)
    "tether_date": ("montsrrat.otf", 110),  # Date format: "14 dec" - size 110
    "tether_year": ("montsrrat.otf", 145),  # Year: "2025" - size 145
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

TETHER_LAYOUT_ORDER = [
    "tether_buy_irr",
    "tether_sell_irr",
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
}


def supports_tether_category(category) -> bool:
    slug = (category.slug or "").lower()
    name = (category.name or "").lower()
    keywords = {"tether", "usdt", "تتر"}
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
        raise FileNotFoundError(
            f"Tether offer background missing at {background_path}."
        )

    image = Image.open(background_path).convert("RGBA")
    draw_ctx = ImageDraw.Draw(image)
    fonts = _load_fonts()

    # Draw date and year on tether board
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
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


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
    """Draw date and year on tether board in English format."""
    # Date format: "14 dec" (day + abbreviated month)
    day = now.day
    month_abbr = now.strftime("%b").lower()  # e.g., "dec"
    date_text = f"{day} {month_abbr}"
    
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["tether_date"],
        date_text,
        font=fonts["tether_date"],
        fill=(0, 0, 0),  # Black color
    )
    
    # Year format: "2025"
    year_text = str(now.year)
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["tether_year"],
        year_text,
        font=fonts["tether_year"],
        fill=(0, 0, 0),  # Black color
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

    if trade == "buy":
        if "gbp" in name or "پوند" in name:
            return "tether_buy_gbp"
        return "tether_buy_irr"
    if trade == "sell":
        if "gbp" in name or "پوند" in name:
            return "tether_sell_gbp"
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


