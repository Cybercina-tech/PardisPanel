from __future__ import annotations

import io
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Optional, Tuple

import jdatetime
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont


try:
    from setting.models import PriceThemeState
except Exception:  # pragma: no cover - optional dependency during migrations/tests
    PriceThemeState = None

USE_ARABIC_RESHAPER = True

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:
    USE_ARABIC_RESHAPER = False

from price_publisher.services.image_renderer import RenderedPriceImage

# Coordinates derived from the legacy pic_generator implementation
DATE_BOX_POSITIONS = {
    "farsi_date": (2290, 290),
    "farsi_weekday": (2150, 470),
    "eng_date": (690, 290),
    "eng_weekday": (730, 470),
}

PRICE_POSITIONS = {
    "buy_from_account": (760, 680),
    "cash_purchase_price": (760, 1030),
    "sell_from_account": (760, 1580),
    "cash_sales_price": (760, 1920),
    "official_sale_price": (760, 2260),
    "lira": (760, 2773),
    "dirham": (760, 3135),
}

STOP_POSITIONS = {
    "buy_from_account": (550, 680),
    "cash_purchase_price": (550, 1030),
    "sell_from_account": (530, 1580),
    "cash_sales_price": (530, 1940),
    "official_sale_price": (530, 2280),
    "lira": (530, 2780),
    "dirham": (530, 3131),
}

CALL_POSITIONS = {
    "buy_from_account": (530, 690),
    "cash_purchase_price": (530, 1030),
    "sell_from_account": (530, 1580),
    "cash_sales_price": (530, 1940),
    "official_sale_price": (530, 2280),
    "lira": (530, 2780),
    "dirham": (530, 3131),
}

LAYOUT_ORDER = [
    "buy_from_account",
    "cash_purchase_price",
    "sell_from_account",
    "cash_sales_price",
    "official_sale_price",
    "lira",
    "dirham",
]

PRICE_TYPE_ALIASES = {
    "buy_from_account": {
        "buy_from_account",
        "buy-from-account",
        "buy_account",
        "خرید_پوند_از_حساب",
        "خرید_از_حساب",
    },
    "cash_purchase_price": {
        "cash_purchase_price",
        "cash-purchase-price",
        "cash_buy_price",
        "cash_purchase",
        "خرید_پوند_نقدی",
        "خرید_نقدی",
    },
    "sell_from_account": {
        "sell_from_account",
        "sell-from-account",
        "sell_account",
        "فروش_پوند_از_حساب",
        "فروش_از_حساب",
    },
    "cash_sales_price": {
        "cash_sales_price",
        "cash-sales-price",
        "cash_sale_price",
        "فروش_پوند_نقدی",
        "فروش_نقدی",
        "فروش_نقدی_پوند",
    },
    "official_sale_price": {
        "offical_sale_price",
        "official_sale_price",
        "official-sales-price",
        "official_sale",
        "فروش_رسمی",
        "نرخ_رسمی",
        "فروش_پوند_رسمی",
        "فروش_رسمی_پوند",
    },
    "lira": {
        "lira",
        "لیر",
        "turkish_lira",
        "try",
    },
    "dirham": {
        "dirham",
        "درهم",
        "uae_dirham",
        "aed",
    },
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

STATIC_ROOT_DIR = Path(settings.BASE_DIR) / "static"
IMAGE_ROOT = STATIC_ROOT_DIR / "img"
FONT_ROOT = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts"))
LEGACY_BACKGROUNDS = getattr(settings, "LEGACY_CATEGORY_BACKGROUNDS", {})


def supports_category(category) -> bool:
    slug = (category.slug or "").lower()
    name = category.name.lower()
    keywords = {"pound", "gbp", "پوند"}
    return any(token in slug for token in keywords) or any(
        token in name for token in keywords
    )


def render_category_board(
    *,
    category,
    price_items: Iterable[Tuple],
    timestamp,
) -> RenderedPriceImage:
    background_path = _resolve_background_for_category(category)
    image = Image.open(background_path).convert("RGBA")
    draw_ctx = ImageDraw.Draw(image)

    fonts = _load_fonts()
    # Always use current time for date display to ensure accuracy
    now = timezone.localtime(timezone.now())
    _draw_dates(draw_ctx, fonts, now)

    price_map = _build_price_map(price_items)

    for index, key in enumerate(LAYOUT_ORDER):
        position = PRICE_POSITIONS[key]
        stop_position = STOP_POSITIONS[key]
        call_position = CALL_POSITIONS[key]
        entry = price_map.get(key)
        if not entry:
            continue

        display_text, font_key, target_position = _resolve_display_value(
            entry["history"],
            index,
            price_position=position,
            stop_position=stop_position,
            call_position=call_position,
        )
        draw_ctx.text(
            target_position,
            display_text,
            font=fonts[font_key],
            fill="white",
        )

    buffer = io.BytesIO()
    buffer.name = "prices.png"
    image.convert("RGB").save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


def _resolve_background_for_category(category) -> Path:
    slug = (category.slug or "").lower()
    name = category.name.lower()

    # Check if this is a pound/GBP category - use rotating backgrounds
    is_pound = any(keyword in slug or keyword in name for keyword in ["pound", "gbp", "پوند"])
    
    if is_pound:
        # Use rotating background for pound categories
        rotating = _get_rotating_background()
        if rotating is not None:
            return rotating

    def candidate(keys):
        for key in keys:
            if key in LEGACY_BACKGROUNDS:
                return LEGACY_BACKGROUNDS[key]
        return None

    background_rel = candidate(
        [
            slug,
            name,
            "price_theme_default",
        ]
    )

    if background_rel:
        path = IMAGE_ROOT / background_rel
        if path.exists():
            return path

    rotating = _get_rotating_background()
    if rotating is not None:
        return rotating

    raise FileNotFoundError(
        "No legacy price theme background found in static/img/price_theme."
    )


def _get_rotating_background():
    """
    Get the next rotating background from price_theme folder.
    Cycles through all image files (1.jpg, 2.jpg, etc.) in order.
    """
    price_theme_dir = IMAGE_ROOT / "price_theme"
    files = sorted(
        [f for ext in ("*.png", "*.jpg", "*.jpeg") for f in price_theme_dir.glob(ext)],
        key=lambda path: int(path.stem) if path.stem.isdigit() else float('inf'),
    )
    if not files:
        return None

    if PriceThemeState is None:
        return files[0]

    try:
        with transaction.atomic():
            state, _ = PriceThemeState.objects.select_for_update().get_or_create(
                key="price_theme",
                defaults={"last_index": 0},
            )
            # Use current index, then increment for next time
            current_index = state.last_index % len(files)
            next_index = (state.last_index + 1) % len(files)
            state.last_index = next_index
            state.save(update_fields=["last_index", "updated_at"])
    except Exception:
        return files[0]

    return files[current_index]


def _load_fonts():
    fonts = {
        "farsi_date": ImageFont.truetype(str(FONT_ROOT / "Kalameh.ttf"), 110),
        "farsi_weekday": ImageFont.truetype(str(FONT_ROOT / "Kalameh.ttf"), 80),
        "eng_date": ImageFont.truetype(str(FONT_ROOT / "Kalameh.ttf"), 110),
        "eng_weekday": ImageFont.truetype(str(FONT_ROOT / "Kalameh.ttf"), 80),
        "stop": ImageFont.truetype(str(FONT_ROOT / "Morabba.ttf"), 115),
        "call": ImageFont.truetype(str(FONT_ROOT / "Morabba.ttf"), 100),
    }
    
    price_font_path = FONT_ROOT / "Kalameh.ttf"
    if not price_font_path.exists():
        raise FileNotFoundError(
            f"Font file not found: {price_font_path}. "
            f"Please ensure the font file exists in the fonts directory."
        )
    try:
        fonts["price"] = ImageFont.truetype(str(price_font_path), 132)
    except OSError as e:
        raise OSError(
            f"Failed to load font 'Kalameh.ttf': {e}"
        ) from e
    
    return fonts


def _draw_dates(draw_ctx: ImageDraw.ImageDraw, fonts, now):
    today_en = now.strftime("%A")

    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    farsi_date_str = _to_farsi_digits(
        f"{jalali.day} {_farsi_month(jalali.month)} {jalali.year}"
    )
    farsi_weekday = FARSI_WEEKDAYS.get(today_en, "")

    # Persian date + weekday in top-right box
    _draw_centered(
        draw_ctx, _reshape_rtl(farsi_date_str), fonts["farsi_date"],
        *DATE_BOX_POSITIONS["farsi_date"],
    )
    _draw_centered(
        draw_ctx, _reshape_rtl(farsi_weekday), fonts["farsi_weekday"],
        *DATE_BOX_POSITIONS["farsi_weekday"],
    )

    # English date + weekday in top-left box
    eng_day = _to_english_digits(str(now.day))
    eng_year = _to_english_digits(str(now.year))
    eng_date_str = f"{eng_day} {now.strftime('%b')} {eng_year}"
    _draw_centered(
        draw_ctx, eng_date_str, fonts["eng_date"],
        *DATE_BOX_POSITIONS["eng_date"],
    )
    _draw_centered(
        draw_ctx, now.strftime("%A"), fonts["eng_weekday"],
        *DATE_BOX_POSITIONS["eng_weekday"],
    )


def _build_price_map(price_items: Iterable[Tuple]):
    result = {}
    for price_type, price_history in price_items:
        identifiers = [
            price_type.slug or "",
            price_type.name,
            _slugify(price_type.name),
        ]
        target_key = None
        for identifier in identifiers:
            if not identifier:
                continue
            target_key = _match_price_key(identifier)
            if target_key:
                break
        if not target_key:
            continue
        result[target_key] = {
            "price_type": price_type,
            "history": price_history,
        }
    return result


def _match_price_key(identifier: str) -> Optional[str]:
    normalized = _slugify(identifier)
    for key, aliases in PRICE_TYPE_ALIASES.items():
        if normalized in aliases:
            return key
    return None


def _slugify(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .lower()
    )


def _resolve_display_value(
    history,
    index: int,
    *,
    price_position,
    stop_position,
    call_position,
):
    if not history:
        return ("—", "price", price_position)

    note = (history.notes or "").strip().lower()
    if any(token in note for token in ("call", "تماس")):
        return ("تماس بگیرید", "call", call_position)

    if any(token in note for token in ("stop", "توقف")):
        text = "توقف خرید" if index < 2 else "توقف فروش"
        return (text, "stop", stop_position)

    value = _format_price_value(history.price)
    return (value, "price", price_position)


def _format_price_value(value) -> str:
    decimal_value = Decimal(value)
    try:
        integer_value = int(decimal_value.quantize(Decimal("1")))
    except Exception:
        integer_value = int(decimal_value)
    formatted = f"{integer_value:,}"
    return _to_english_digits(formatted)  # Convert to English digits for GBP/USDT prices


def _draw_centered(draw_ctx, text, font, cx, cy, fill="white"):
    bbox = draw_ctx.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw_ctx.text((cx - tw / 2, cy - th / 2), text, font=font, fill=fill)


def _reshape_rtl(text: str) -> str:
    if USE_ARABIC_RESHAPER:
        return get_display(arabic_reshaper.reshape(text))
    return text


def _to_farsi_digits(value: str) -> str:
    return str(value).translate(FARSI_DIGITS)


def _to_english_digits(value: str) -> str:
    return str(value).translate(EN_DIGITS)


def _farsi_month(month_index: int) -> str:
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
    if 0 <= month_index < len(months):
        return months[month_index]
    return ""


