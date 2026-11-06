"""
Build dynamic_data dict for render_price_template from category/special context and SiteSettings.
Maps price items and dates to variable catalog keys.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

import jdatetime
from django.utils import timezone

from setting.models import SiteSettings

from core.utils import format_price_display


def _normalize(s: str) -> str:
    return (s or "").strip().replace(" ", "").replace("-", "").replace("_", "").replace("‌", "").lower()


# Map legacy/canonical price keys to our variable catalog keys (category board)
CATEGORY_KEY_MAP = {
    "cash_purchase_price": "price_cash_buy",
    "buy_from_account": "price_account_buy",
    "cash_sales_price": "price_cash_sell",
    "sell_from_account": "price_account_sell",
    "official_sale_price": "price_official_sell",
    "lira": "price_lira",
    "dirham": "price_dirham",
}

# Aliases for category board: normalized identifier -> canonical key
CATEGORY_ALIASES: Dict[str, str] = {}
for _canon, _aliases in (
    ("cash_purchase_price", ("cash_purchase_price", "cash-purchase-price", "cash_buy_price", "خرید_نقدی", "خرید پوند نقدی")),
    ("buy_from_account", ("buy_from_account", "buy-from-account", "buy_account", "خرید_از_حساب", "خرید پوند از حساب")),
    ("cash_sales_price", ("cash_sales_price", "cash-sales-price", "cash_sale_price", "فروش_نقدی", "فروش پوند نقدی")),
    ("sell_from_account", ("sell_from_account", "sell-from-account", "sell_account", "فروش_از_حساب", "فروش پوند از حساب")),
    ("official_sale_price", ("official_sale_price", "official-sale-price", "فروش_رسمی", "نرخ_رسمی")),
    ("lira", ("lira", "لیر", "turkish_lira", "try")),
    ("dirham", ("dirham", "درهم", "uae_dirham", "aed")),
):
    for a in _aliases:
        CATEGORY_ALIASES[_normalize(a)] = _canon

# Tether: variable keys are same as canonical
TETHER_ALIASES: Dict[str, str] = {}
for _canon, _aliases in (
    ("tether_buy_irr", ("tether_buy_irr", "buy_tether_irr", "tether_buy_toman", "خرید_تتر_تومان", "خریدتترتومن")),
    ("tether_sell_irr", ("tether_sell_irr", "sell_tether_irr", "tether_sell_toman", "فروش_تتر_تومان", "فروشتترتومن")),
    ("tether_buy_gbp", ("tether_buy_gbp", "buy_tether_gbp", "خرید_تتر_پوند", "خریدتترپوند")),
    ("tether_sell_gbp", ("tether_sell_gbp", "sell_tether_gbp", "فروش_تتر_پوند", "فروشتترپوند")),
):
    for a in _aliases:
        TETHER_ALIASES[_normalize(a)] = _canon

FARSI_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}
PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _format_price(price) -> str:
    return format_price_display(price)


def _match_category_key(price_type) -> Optional[str]:
    """Resolve price_type to canonical category key, then to variable key."""
    name = getattr(price_type, "name", "") or ""
    slug = getattr(price_type, "slug", "") or ""
    norm_name = _normalize(name)
    norm_slug = _normalize(slug)
    canonical = CATEGORY_ALIASES.get(norm_name) or CATEGORY_ALIASES.get(norm_slug)
    if canonical:
        return CATEGORY_KEY_MAP.get(canonical, canonical)
    return None


def _match_tether_key(price_type) -> Optional[str]:
    norm_name = _normalize(getattr(price_type, "name", "") or "")
    norm_slug = _normalize(getattr(price_type, "slug", "") or "")
    return TETHER_ALIASES.get(norm_name) or TETHER_ALIASES.get(norm_slug)


def _dates_from_timestamp(timestamp) -> Dict[str, str]:
    # Always use current local time at render-time for date/clock widgets.
    # We intentionally ignore the incoming price-history timestamp so templates
    # show "today" consistently in preview and final publication.
    now = timezone.localtime()
    jd = jdatetime.date.fromgregorian(date=now.date())
    farsi_date = f"{jd.day} {_farsi_month(jd.month)} {jd.year}"
    farsi_date = farsi_date.translate(PERSIAN_DIGITS)
    # Jalali compact formats (Persian digits)
    date_fa_slash = f"{jd.year}/{jd.month:02d}/{jd.day:02d}".translate(PERSIAN_DIGITS)
    date_fa_slash_short = f"{jd.year}/{jd.month}/{jd.day}".translate(PERSIAN_DIGITS)
    date_fa_iso = f"{jd.year:04d}-{jd.month:02d}-{jd.day:02d}".translate(PERSIAN_DIGITS)
    farsi_weekday = FARSI_WEEKDAYS.get(now.strftime("%A"), "")
    english_date = now.strftime("%B %d, %Y")
    english_weekday = now.strftime("%A")
    date_en_iso = now.strftime("%Y-%m-%d")
    date_en_dmy = now.strftime("%d/%m/%Y")
    date_en_mdy = now.strftime("%m/%d/%Y")
    date_en_short = now.strftime("%d %b %Y")
    date_en_weekday_long = now.strftime("%A, %B %d, %Y")
    tether_date = now.strftime("%d %b").lower()
    tether_year = now.strftime("%Y")
    time_str = now.strftime("%H:%M")
    return {
        "date_fa": farsi_date,
        "date_en": english_date,
        "farsi_date": farsi_date,
        "date_fa_slash": date_fa_slash,
        "date_fa_slash_short": date_fa_slash_short,
        "date_fa_iso": date_fa_iso,
        "farsi_weekday": farsi_weekday,
        "weekday_fa": farsi_weekday,
        "english_date": english_date,
        "english_weekday": english_weekday,
        "weekday_en": english_weekday,
        "date_en_iso": date_en_iso,
        "date_en_dmy": date_en_dmy,
        "date_en_mdy": date_en_mdy,
        "date_en_short": date_en_short,
        "date_en_weekday_long": date_en_weekday_long,
        "tether_date": tether_date,
        "tether_year": tether_year,
        "time": time_str,
    }


def _farsi_month(m: int) -> str:
    months = [
        "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    ]
    return months[m] if 1 <= m <= 12 else ""


def _branding_from_site() -> Dict[str, str]:
    s = SiteSettings.load()
    return {
        "working_hours": (s.business_hours or "").strip() or "دوشنبه تا شنبه: 9:30 صبح تا ۱۷",
        "phone": s.support_phone or "",
        "channel_username": getattr(s, "site_name", "") or "Sarafi Pardis",
        "website": "",
    }


def _slug_binding_key(price_type) -> Optional[str]:
    slug = getattr(price_type, "slug", None) or ""
    slug = str(slug).strip()
    if not slug:
        return None
    return f"price__{slug}"


def _trade_binding_key(price_type) -> Optional[str]:
    trade_type = str(getattr(price_type, "trade_type", "") or "").strip().lower()
    if trade_type not in ("buy", "sell"):
        return None
    slug = str(getattr(price_type, "slug", "") or "").strip()
    if slug:
        return f"price_{trade_type}__{slug}"
    return None


def _register_caption_price_tokens(price_type, formatted: str, data: dict) -> None:
    """Bare slug/name keys for captions like {خرید-یورو} (UI inserts slug, not price__slug)."""
    slug = str(getattr(price_type, "slug", "") or "").strip()
    name = str(getattr(price_type, "name", "") or "").strip()
    if slug:
        data[slug] = formatted
    if name:
        data[name] = formatted


def build_dynamic_data_for_category_board(
    category,
    price_items: Iterable[Tuple[Any, Any]],
    timestamp,
) -> Dict[str, str]:
    """Build dynamic_data for category_board usage (e.g. GBP)."""
    data = {}
    data.update(_dates_from_timestamp(timestamp))
    data.update(_branding_from_site())
    data["pair_name"] = (category.name or "") if category else ""

    for price_type, price_history in price_items:
        price = getattr(price_history, "price", None) or getattr(price_history, "value", None)
        formatted = _format_price(price)
        pt_pk = getattr(price_type, "pk", None) or getattr(price_type, "id", None)
        if pt_pk is not None:
            data[f"price_type__{int(pt_pk)}"] = formatted
        bk = _slug_binding_key(price_type)
        if bk:
            data[bk] = formatted
        tb = _trade_binding_key(price_type)
        if tb:
            data[tb] = formatted
        key = _match_category_key(price_type)
        if key:
            data[key] = formatted
        _register_caption_price_tokens(price_type, formatted, data)
    return data


def build_dynamic_data_for_tether_board(
    category,
    price_items: Iterable[Tuple[Any, Any]],
    timestamp,
) -> Dict[str, str]:
    """Build dynamic_data for tether_board usage."""
    data = {}
    data.update(_dates_from_timestamp(timestamp))
    data.update(_branding_from_site())
    data["pair_name"] = (category.name or "") if category else ""

    for price_type, price_history in price_items:
        price = getattr(price_history, "price", None) or getattr(price_history, "value", None)
        formatted = _format_price(price)
        pt_pk = getattr(price_type, "pk", None) or getattr(price_type, "id", None)
        if pt_pk is not None:
            data[f"price_type__{int(pt_pk)}"] = formatted
        bk = _slug_binding_key(price_type)
        if bk:
            data[bk] = formatted
        tb = _trade_binding_key(price_type)
        if tb:
            data[tb] = formatted
        key = _match_tether_key(price_type)
        if key:
            data[key] = formatted
        _register_caption_price_tokens(price_type, formatted, data)
    return data


def build_dynamic_data_for_special_offer(
    special_price_type,
    price_history,
    category_price_type=None,
) -> Dict[str, str]:
    """Build dynamic_data for special_offer usage."""
    data = {}
    timestamp = getattr(price_history, "updated_at", None) or getattr(price_history, "created_at", None) or timezone.now()
    data.update(_dates_from_timestamp(timestamp))
    data.update(_branding_from_site())
    data["pair_name"] = getattr(special_price_type, "name", "") or ""
    price = getattr(price_history, "price", None) or getattr(price_history, "value", None)
    data["price"] = _format_price(price)
    sp_pk = getattr(special_price_type, "pk", None) or getattr(special_price_type, "id", None)
    if sp_pk is not None:
        data[f"price_type__{int(sp_pk)}"] = data["price"]
    if category_price_type is not None:
        cat_pt_pk = getattr(category_price_type, "pk", None) or getattr(category_price_type, "id", None)
        if cat_pt_pk is not None:
            data[f"price_type__{int(cat_pt_pk)}"] = data["price"]
        cat_slug = str(getattr(category_price_type, "slug", "") or "").strip()
        if cat_slug:
            data[f"price__{cat_slug}"] = data["price"]
        _register_caption_price_tokens(category_price_type, data["price"], data)
    sp_slug = getattr(special_price_type, "slug", None) or ""
    sp_slug = str(sp_slug).strip()
    if sp_slug:
        data[f"price__{sp_slug}"] = data["price"]
        data[sp_slug] = data["price"]
    sp_name = str(getattr(special_price_type, "name", "") or "").strip()
    if sp_name:
        data[sp_name] = data["price"]
    # Map special GBP-style keys if name matches
    name_norm = _normalize(getattr(special_price_type, "name", "") or "")
    if "خرید" in name_norm or "buy" in name_norm:
        if "نقد" in name_norm or "cash" in name_norm:
            data["special_buy_cash_gbp_price"] = data["price"]
        else:
            data["special_buy_account_gbp_price"] = data["price"]
    elif "فروش" in name_norm or "sell" in name_norm:
        if "نقد" in name_norm or "cash" in name_norm:
            data["special_sell_cash_gbp_price"] = data["price"]
        else:
            data["special_sell_account_gbp_price"] = data["price"]
    return data
