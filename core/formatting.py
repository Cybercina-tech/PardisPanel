"""
Shared formatting utilities for digit conversion, price display, and Persian text.
Single source of truth -- replaces duplicates in legacy_category_renderer,
tether_renderer, special_offer_renderer, and publisher.
"""
from decimal import Decimal, InvalidOperation


FARSI_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
PERSIAN_DIGITS = FARSI_DIGITS  # alias used by publisher.py

FARSI_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}

FARSI_MONTHS = [
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


def to_farsi_digits(value: str) -> str:
    return str(value).translate(FARSI_DIGITS)


def to_english_digits(value: str) -> str:
    return str(value).translate(EN_DIGITS)


def farsi_month(index: int) -> str:
    if 0 <= index < len(FARSI_MONTHS):
        return FARSI_MONTHS[index]
    return ""


def format_price_dynamic(value) -> str:
    """Format a price with dynamic decimals: 100 -> '100', 100.5 -> '100.5', 100.00 -> '100'.
    Returns comma-separated string with English digits."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        return str(value)

    if d == d.to_integral_value():
        return f"{int(d):,}"

    normalized = d.normalize()
    int_part = int(normalized)
    frac_part = normalized - int_part
    frac_str = str(frac_part).lstrip("0").lstrip(".")
    return f"{int_part:,}.{frac_str}"
