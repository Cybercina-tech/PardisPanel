from __future__ import annotations

import io
import functools
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
MEDIA_ROOT = Path(settings.MEDIA_ROOT)
FONT_ROOT = Path(
    getattr(settings, "PRICE_RENDERER_FONT_ROOT", STATIC_ROOT_DIR / "fonts")
)

# Constants for special GBP templates
SPECIAL_GBP_TEMPLATE_POSITION = (480, 1040)
SPECIAL_GBP_TEMPLATE_FONT = ("montsrrat.otf", 130)
SPECIAL_GBP_TEMPLATES = (
    "special_buy_cash_GBP.jpg",
    "special_buy_account_GBP.jpg",
    "special_sell_cash_GBP.jpg",
    "special_sell_account_GBP.jpg",
)

# Double-price banners: one image for Buy, one for Sell (1760×716).
# Files live under MEDIA_ROOT/templates/. Resolved by slug first (see DOUBLE_PRICE_BACKGROUND_BY_SLUG).
# Top bar = Account (حسابی), bottom bar = Cash (نقدی). Font: Montserrat (montsrrat.otf) size 58.
# Both banners use white price pills — black price text on both.
# Date: Montserrat 34 at top-right (1480, 48). Buy: black text; Sell: white text.
DOUBLE_BUY_BACKGROUND = "gbp_special_buy_banner.png"
DOUBLE_SELL_BACKGROUND = "gbp_special_sell_banner.png"
DOUBLE_PRICE_BACKGROUND_BY_SLUG = {
    "special-gbp-buy": DOUBLE_BUY_BACKGROUND,
    "special-gbp-sell": DOUBLE_SELL_BACKGROUND,
}
# Legacy filenames kept for reference / manual cleanup on servers.
LEGACY_DOUBLE_BUY_BACKGROUND = "special_gbp_buy_double.png"
LEGACY_DOUBLE_SELL_BACKGROUND = "special_gbp_sell_double.png"
DOUBLE_ACCOUNT_BAR_XY = (375, 258)   # Top bar - Account (حسابی)
DOUBLE_CASH_BAR_XY = (375, 382)      # Bottom bar - Cash (نقدی)
DOUBLE_PRICE_FONT = ("montsrrat.otf", 58)
DOUBLE_DATE_XY = (1480, 48)
DOUBLE_DATE_FONT = ("montsrrat.otf", 34)
DOUBLE_DATE_FILL_SELL = (255, 255, 255)  # White on dark sell banner
DOUBLE_DATE_FILL_BUY = (0, 0, 0)        # Black on light buy banner
DOUBLE_PRICE_FILL = (0, 0, 0)            # Black on white price pills (both banners)

OFFER_TEXT_POSITIONS = {
    "farsi_date": (1900, 250),
    "farsi_weekday": (1860, 420),
    "english_date": (420, 250),
    "english_weekday": (580, 420),
    "price": (360, 2100),
    "working_hours": (1200, 2200),  # ساعات کاری
    # Special positions for GBP templates (all use same position)
    "special_buy_cash_gbp_price": SPECIAL_GBP_TEMPLATE_POSITION,
    "special_buy_account_gbp_price": SPECIAL_GBP_TEMPLATE_POSITION,
    "special_sell_cash_gbp_price": SPECIAL_GBP_TEMPLATE_POSITION,
    "special_sell_account_gbp_price": SPECIAL_GBP_TEMPLATE_POSITION,
}

FONT_DEFINITIONS = {
    "farsi_date": ("Morabba.ttf", 115),
    "farsi_weekday": ("Morabba.ttf", 86),
    "english_date": ("montsrrat.otf", 100),  # Changed to English font
    "english_weekday": ("montsrrat.otf", 95),  # Changed to English font
    "english_number": ("montsrrat.otf", 115),  # Changed to English font
    "price": ("montsrrat.otf", 220),
    "working_hours": ("Morabba.ttf", 50),  # ساعات کاری
    # Special fonts for GBP templates (all use same font as Tether)
    "special_buy_cash_gbp_price": SPECIAL_GBP_TEMPLATE_FONT,
    "special_buy_account_gbp_price": SPECIAL_GBP_TEMPLATE_FONT,
    "special_sell_cash_gbp_price": SPECIAL_GBP_TEMPLATE_FONT,
    "special_sell_account_gbp_price": SPECIAL_GBP_TEMPLATE_FONT,
    # Double-price banners (نقدی و حسابی): Montserrat 85 for prices
    "double_price": DOUBLE_PRICE_FONT,
    # Double-price date: English "26 Feb 2026", Montserrat 50
    "double_price_date": DOUBLE_DATE_FONT,
}

from core.formatting import (
    FARSI_WEEKDAYS,
    FARSI_DIGITS,
    EN_DIGITS,
    to_farsi_digits as _to_farsi_digits,
    to_english_digits as _to_english_digits,
    farsi_month as _farsi_month,
)


def normalize_identifier(value: str) -> str:
    """Normalize a string identifier by removing spaces, dashes, underscores and converting to lowercase."""
    return (
        (value or "")
        .strip()
        .replace("‌", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .lower()
    )


# Backward compatibility alias
_normalize = normalize_identifier


@dataclass(frozen=True)
class SpecialOfferTemplate:
    background: str
    aliases: set[str]


_SPECIAL_TEMPLATE_DEFINITIONS: Sequence[tuple[str, Iterable[str]]] = (
    (
        "special_buy_cash_GBP.jpg",  # Changed to use media/templates/special_buy_cash_GBP.jpg
        (
            "خرید نقدی پوند ویژه",
            "خریدنقدیپوندویژه",
            "خرید ویژه نقدی",  # Added: خرید ویژه نقدی
            "خریدویژهنقدی",
            "buycashpoundspecial",
            "specialbuycashgbp",
            "special_buy_cash_gbp",
            "buycashgbpspecial",
            "buycashspecial",  # Added: buycashspecial for "خرید ویژه نقدی"
            "specialcashpurchase",
        ),
    ),
    (
        "offer1.png",
        (
            "offer1",
        ),
    ),
    (
        "special_buy_account_GBP.jpg",  # Changed to use media/templates/special_buy_account_GBP.jpg
        (
            "خرید ویژه از حساب",
            "خریدویژهازحساب",
            "buyaccountspecial",
            "specialbuyaccountgbp",
            "special_buy_account_gbp",
            "buyaccountgbpspecial",
        ),
    ),
    (
        "offer2.png",
        (
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
        "special_sell_cash_GBP.jpg",  # Changed to use media/templates/special_sell_cash_GBP.jpg
        (
            "فروش ویژه نقدی",
            "فروشویژهنقدی",
            "sellcashspecial",
            "specialselcashgbp",
            "special_sell_cash_gbp",
            "sellcashgbpspecial",
        ),
    ),
    (
        "offer4.png",
        (
            "offer4",
        ),
    ),
    (
        "special_sell_account_GBP.jpg",  # Changed to use media/templates/special_sell_account_GBP.jpg
        (
            "فروش ویژه از حساب",
            "فروشویژهازحساب",
            "sellaccountspecial",
            "specialselaccountgbp",
            "special_sell_account_gbp",
            "sellaccountgbpspecial",
        ),
    ),
    (
        "offer5.png",
        (
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
        aliases={normalize_identifier(alias) for alias in aliases},
    )
    for background, aliases in _SPECIAL_TEMPLATE_DEFINITIONS
)


def resolve_special_offer_template(special_price_type) -> Optional[SpecialOfferTemplate]:
    """Resolve the special offer template for a given special price type."""
    return _resolve_template(special_price_type)


def supports_special_offer_type(special_price_type) -> bool:
    """Return True if the given special price type has a bespoke offer template."""
    return resolve_special_offer_template(special_price_type) is not None


def supports_double_price_type(special_price_type) -> bool:
    """Return True if the special price type uses double-price banners (Cash + Account on one image)."""
    return getattr(special_price_type, "is_double_price", False)


def render_double_price_board(
    *,
    special_price_type,
    price_history,
) -> RenderedPriceImage:
    """
    Render a double-price banner: Account price on top bar, Cash price on bottom bar.
    Uses gbp_special_buy_banner.png (Buy) and gbp_special_sell_banner.png (Sell).
    Backgrounds must exist under MEDIA_ROOT/templates/. Font: English word font (montsrrat).
    """
    trade_type = (getattr(special_price_type, "trade_type", "") or "").strip().lower()
    slug = (getattr(special_price_type, "slug", "") or "").strip()
    background_name = DOUBLE_PRICE_BACKGROUND_BY_SLUG.get(slug)
    if not background_name:
        if trade_type == "buy":
            background_name = DOUBLE_BUY_BACKGROUND
        elif trade_type == "sell":
            background_name = DOUBLE_SELL_BACKGROUND
        else:
            raise ValueError(f"Unknown trade_type for double-price: {trade_type}")
    price_fill = DOUBLE_PRICE_FILL

    background_path = _resolve_double_price_background_path(background_name)

    image = _open_background(background_path).copy()
    draw_ctx = ImageDraw.Draw(image)
    fonts = _load_fonts()

    # English date on double-price banners: e.g. "10 Jun 2026", Montserrat 34 at top-right.
    timestamp = _extract_timestamp(price_history)
    if timestamp:
        localized = timezone.localtime(timestamp)
        date_text = localized.strftime("%d %b %Y")  # e.g. 26 Feb 2026
    else:
        date_text = timezone.localtime().strftime("%d %b %Y")
    date_font = fonts.get("double_price_date") or fonts.get("english_number")
    if date_font:
        date_fill = DOUBLE_DATE_FILL_SELL if trade_type == "sell" else DOUBLE_DATE_FILL_BUY
        draw_ctx.text(
            DOUBLE_DATE_XY,
            date_text,
            font=date_font,
            fill=date_fill,
        )

    price_font = fonts.get("double_price") or fonts.get("english_number") or fonts.get("price")

    # Build a minimal object so _format_price_value can read .price and .notes
    class _PriceHolder:
        pass

    cash_holder = _PriceHolder()
    cash_holder.price = getattr(price_history, "cash_price", None) or getattr(price_history, "price", None)
    cash_holder.notes = getattr(price_history, "notes", None)
    cash_text = _format_price_value(cash_holder, special_price_type=special_price_type)

    account_holder = _PriceHolder()
    account_holder.price = getattr(price_history, "account_price", None) or getattr(price_history, "price", None)
    account_holder.notes = getattr(price_history, "notes", None)
    account_text = _format_price_value(account_holder, special_price_type=special_price_type)

    # Top bar = Account (حسابی), bottom bar = Cash (نقدی)
    draw_ctx.text(
        DOUBLE_ACCOUNT_BAR_XY,
        account_text,
        font=price_font,
        fill=price_fill,
    )
    draw_ctx.text(
        DOUBLE_CASH_BAR_XY,
        cash_text,
        font=price_font,
        fill=price_fill,
    )

    working_hours_text = "ساعات کاری:\nدوشنبه تا شنبه: ۹:۳۰ صبح تا ۵:۰۰ عصر\nیکشنبه: تعطیل"
    working_hours_lines = working_hours_text.split("\n")
    working_hours_y = OFFER_TEXT_POSITIONS["working_hours"][1]
    working_hours_font = fonts.get("working_hours")
    if working_hours_font:
        for i, line in enumerate(working_hours_lines):
            draw_ctx.text(
                (OFFER_TEXT_POSITIONS["working_hours"][0], working_hours_y + i * 60),
                line,
                font=working_hours_font,
                fill=(255, 255, 255),
            )

    buffer = io.BytesIO()
    buffer.name = background_name
    image.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


def render_special_offer_board(
    *,
    special_price_type,
    price_history,
) -> RenderedPriceImage:
    """Render the pound special-offer board using branded templates."""
    template = _resolve_template(special_price_type)
    if not template:
        raise ValueError("No offer template configured for this special price type.")

    # Determine background path (media/templates for special GBP, static/offer for others)
    background_path = _get_template_background_path(template.background)
    
    if not background_path.exists():
        raise FileNotFoundError(
            f"Offer background missing at {background_path.relative_to(settings.BASE_DIR)}."
        )

    image = _open_background(background_path).copy()
    draw_ctx = ImageDraw.Draw(image)
    fonts = _load_fonts()

    timestamp = _extract_timestamp(price_history)
    # Only draw dates for non-special GBP templates
    if not _is_special_gbp_template(template.background):
        _draw_dates(draw_ctx, fonts, timestamp)

    price_text = _format_price_value(
        price_history, special_price_type=special_price_type
    )
    
    # Get position and font for this template
    price_position, price_font = _get_price_rendering_config(template.background, fonts)
    
    draw_ctx.text(
        price_position,
        price_text,
        font=price_font,
        fill=(0, 0, 0),  # Completely black color
    )
    
    # اضافه کردن ساعات کاری
    working_hours_text = "ساعات کاری:\nدوشنبه تا شنبه: ۹:۳۰ صبح تا ۵:۰۰ عصر\nیکشنبه: تعطیل"
    working_hours_lines = working_hours_text.split('\n')
    working_hours_y = OFFER_TEXT_POSITIONS["working_hours"][1]
    working_hours_font = fonts.get("working_hours")
    if working_hours_font:
        for i, line in enumerate(working_hours_lines):
            draw_ctx.text(
                (OFFER_TEXT_POSITIONS["working_hours"][0], working_hours_y + i * 60),
                line,
                font=working_hours_font,
                fill=(255, 255, 255)
    )

    buffer = io.BytesIO()
    buffer.name = template.background
    image.convert("RGB").save(buffer, format="PNG")
    buffer.seek(0)
    return RenderedPriceImage(stream=buffer, width=image.width, height=image.height)


_BACKGROUND_CACHE: dict[tuple[str, float], Image.Image] = {}


def _resolve_double_price_background_path(background_name: str) -> Path:
    """Resolve a double-price banner file, with legacy filename fallback."""
    templates_dir = MEDIA_ROOT / "templates"
    candidates = [background_name]
    if background_name == DOUBLE_BUY_BACKGROUND:
        candidates.append(LEGACY_DOUBLE_BUY_BACKGROUND)
    elif background_name == DOUBLE_SELL_BACKGROUND:
        candidates.append(LEGACY_DOUBLE_SELL_BACKGROUND)

    for name in candidates:
        path = templates_dir / name
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Double-price background missing. Tried: "
        f"{', '.join(str((templates_dir / name).relative_to(settings.BASE_DIR)) for name in candidates)}"
    )


def _open_background(path: Path) -> Image.Image:
    """Load a background image; cache invalidates automatically when the file changes."""
    resolved = Path(path).resolve()
    mtime = resolved.stat().st_mtime
    cache_key = (str(resolved), mtime)
    cached = _BACKGROUND_CACHE.get(cache_key)
    if cached is not None:
        return cached

    for key in list(_BACKGROUND_CACHE):
        if key[0] == str(resolved):
            del _BACKGROUND_CACHE[key]

    img = Image.open(resolved).convert("RGBA")
    img.load()
    _BACKGROUND_CACHE[cache_key] = img
    return img


def _resolve_template(special_price_type) -> Optional[SpecialOfferTemplate]:
    identifiers = _collect_identifiers(special_price_type)
    if not identifiers:
        return None

    normalized = {normalize_identifier(identifier) for identifier in identifiers}
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


@functools.lru_cache(maxsize=1)
def _load_fonts():
    fonts = {}
    for key, (filename, size) in FONT_DEFINITIONS.items():
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
    
    farsi_weekday = FARSI_WEEKDAYS.get(localized.strftime("%A"), "")
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["farsi_weekday"],
        farsi_weekday,
        font=fonts["farsi_weekday"],
        fill="white",
    )

    english_date = localized.strftime("%Y %b %d")
    draw_ctx.text(
        OFFER_TEXT_POSITIONS["english_date"],
        english_date,  # Keep English digits for GBP/USDT prices
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
        return str(value)  # Keep English digits for GBP/USDT prices

    if decimal_value == decimal_value.to_integral():
        decimal_value = decimal_value.quantize(Decimal("1"))

    text = f"{decimal_value:,}"
    # Keep English digits for GBP, USDT and special prices
    return text


def _extract_timestamp(price_history):
    return getattr(price_history, "updated_at", None) or getattr(
        price_history, "created_at", None
    )




def _is_special_gbp_template(background: str) -> bool:
    """Check if template is a special GBP template that uses media/templates path."""
    return background in SPECIAL_GBP_TEMPLATES


def _get_template_background_path(background: str) -> Path:
    """Get the full path to template background image."""
    if _is_special_gbp_template(background):
        return MEDIA_ROOT / "templates" / background
    return OFFER_ROOT / background


def _get_price_rendering_config(background: str, fonts: dict) -> tuple[tuple[int, int], ImageFont.FreeTypeFont]:
    """Get position and font configuration for price rendering based on template background."""
    if background in SPECIAL_GBP_TEMPLATES:
        # Map template name to font key
        template_to_font_key = {
            "special_buy_cash_GBP.jpg": "special_buy_cash_gbp_price",
            "special_buy_account_GBP.jpg": "special_buy_account_gbp_price",
            "special_sell_cash_GBP.jpg": "special_sell_cash_gbp_price",
            "special_sell_account_GBP.jpg": "special_sell_account_gbp_price",
        }
        font_key = template_to_font_key.get(background)
        if font_key:
            return OFFER_TEXT_POSITIONS[font_key], fonts[font_key]
    
    # Default configuration for regular templates
    return OFFER_TEXT_POSITIONS["price"], fonts["price"]



