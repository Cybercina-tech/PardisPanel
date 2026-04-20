"""
Shared sorting utilities for price types and categories.
Single source of truth -- replaces duplicates in change_price/views,
finalize/views, and change_price/templatetags.
"""
from __future__ import annotations

from typing import Iterable, Sequence


def _normalize_price_type_label(value: str) -> str:
    """Same rules as special_offer normalize_identifier (avoid cross-app import cycles)."""
    return (
        (value or "")
        .strip()
        .replace("\u200c", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("_", "")
        .lower()
    )


# Tether banner rows (top → bottom) — must match tether_renderer.TETHER_LAYOUT_ORDER semantics.
TETHER_BANNER_UPDATE_NAME_ORDER: Sequence[str] = (
    "یورو",
    "درهم",
    "لیر",
    "خرید تتر به پوند",
    "فروش تتر به پوند",
)


def is_tether_category(category) -> bool:
    cname = getattr(category, "name", None) or ""
    lower = cname.lower()
    return "تتر" in cname or "tether" in lower or "usdt" in lower


def price_types_for_finalize(category, price_types) -> list:
    """
    Price types shown on finalize dashboard and passed to image publishers.
    Tether: only the five banner rows (excludes mis-filed GBP cash rows, etc.).
    """
    items = list(price_types)
    lower = (category.name or "").lower()
    if "پوند" in category.name or "pound" in lower or "gbp" in lower:
        return list(sort_gbp_price_types(items))
    if is_tether_category(category):
        return tether_banner_price_types_for_update(items)
    return sort_price_types_by_category(items, category.name)


def tether_banner_price_types_for_update(price_types) -> list:
    """
    Only the five rows shown on the tether EUR/AED/TRY + GBP banner.
    Excludes IRR toman rows and stray GBP cash rows under tether category.
    """
    allowed = {_normalize_price_type_label(n) for n in TETHER_BANNER_UPDATE_NAME_ORDER}
    order_map = {
        _normalize_price_type_label(n): i for i, n in enumerate(TETHER_BANNER_UPDATE_NAME_ORDER)
    }
    filtered = [
        pt
        for pt in price_types
        if _normalize_price_type_label(getattr(pt, "name", "") or "") in allowed
    ]
    filtered.sort(
        key=lambda pt: order_map.get(
            _normalize_price_type_label(getattr(pt, "name", "") or ""), 99
        )
    )
    return filtered


def sort_gbp_price_types(price_types):
    """
    Sort price types for GBP/Pound category:
    1. خرید نقدی (Buy Cash)
    2. خرید از حساب (Buy Account)
    3. فروش از حساب (Sell Account)
    4. فروش نقدی (Sell Cash)
    5. فروش رسمی (Sell Official)
    6. لیر (Lira)
    7. درهم (Dirham)
    """
    if not price_types:
        return price_types

    price_types_list = list(price_types)

    def _key(pt):
        name = pt.name
        name_lower = name.lower()
        slug_lower = (getattr(pt, "slug", "") or "").lower()
        trade_type = pt.trade_type.lower()

        if "لیر" in name or slug_lower == "lira":
            return 6
        if "درهم" in name or slug_lower == "dirham":
            return 7

        if trade_type == "buy":
            if "نقدی" in name or "نقد" in name or "cash" in name_lower:
                return 1
            if "حساب" in name or "account" in name_lower:
                return 2
            return 10
        if trade_type == "sell":
            if "حساب" in name or "account" in name_lower:
                return 3
            if "نقد" in name or "cash" in name_lower:
                return 4
            if "رسمی" in name or "official" in name_lower:
                return 5
            return 20
        return 30

    return sorted(price_types_list, key=_key)


def sort_tether_price_types(price_types):
    """
    Sort price types for Tether category:
    1. خرید تتر تومان (Buy Tether Toman/IRR)
    2. فروش تتر تومان (Sell Tether Toman/IRR)
    3. خرید تتر پوند (Buy Tether GBP)
    4. فروش تتر پوند (Sell Tether GBP)
    5. خرید/فروش تتر یورو (Buy/Sell Tether EUR)
    6. خرید/فروش تتر لیر (Buy/Sell Tether TRY)
    7. خرید/فروش تتر درهم (Buy/Sell Tether AED)
    """
    if not price_types:
        return price_types

    price_types_list = list(price_types)

    def _key(pt):
        name_lower = pt.name.lower()
        trade_type = pt.trade_type.lower()
        target_code = (
            getattr(pt.target_currency, "code", "").lower()
            if pt.target_currency
            else ""
        )
        target_name = (
            pt.target_currency.name.lower() if pt.target_currency else ""
        )

        has_toman = (
            any(kw in name_lower for kw in ("تومان", "تومن", "toman", "tmn"))
            or any(kw in target_code for kw in ("irr", "irt"))
            or "تومان" in target_name
            or "تومن" in target_name
        )
        has_gbp = (
            any(kw in name_lower for kw in ("پوند", "pound", "gbp"))
            or "gbp" in target_code
            or "pound" in target_name
            or "پوند" in target_name
        )
        has_eur = (
            any(kw in name_lower for kw in ("یورو", "euro", "eur"))
            or "eur" in target_code
            or "euro" in target_name
            or "یورو" in target_name
        )
        has_try = (
            any(kw in name_lower for kw in ("لیر", "lira", "try"))
            or "try" in target_code
            or "lira" in target_name
            or "لیر" in target_name
        )
        has_aed = (
            any(kw in name_lower for kw in ("درهم", "dirham", "aed"))
            or "aed" in target_code
            or "dirham" in target_name
            or "درهم" in target_name
        )

        if trade_type == "buy":
            if has_gbp:
                return 3
            if has_eur:
                return 5
            if has_try:
                return 6
            if has_aed:
                return 7
            if has_toman:
                return 1
            return 10
        if trade_type == "sell":
            if has_gbp:
                return 4
            if has_eur:
                return 5
            if has_try:
                return 6
            if has_aed:
                return 7
            if has_toman:
                return 2
            return 20
        return 30

    return sorted(price_types_list, key=_key)


def sort_price_types_by_category(price_types, category_name: str):
    """Dispatch to the right sorter based on category name."""
    if not price_types or not category_name:
        return price_types

    lower = category_name.lower()
    if any(kw in category_name for kw in ("تتر",)) or any(
        kw in lower for kw in ("tether", "usdt")
    ):
        return sort_tether_price_types(price_types)
    if any(kw in category_name for kw in ("پوند",)) or any(
        kw in lower for kw in ("pound", "gbp")
    ):
        return sort_gbp_price_types(price_types)
    return price_types


def sort_categories(categories: Iterable) -> list:
    """Sort categories: GBP/Pound first, then Tether/USDT, then others alphabetically."""

    def _key(cat):
        name = (cat.name or "").lower()
        if "پوند" in cat.name or "pound" in name or "gbp" in name:
            return (0, name)
        if "تتر" in cat.name or "tether" in name or "usdt" in name:
            return (1, name)
        return (2, name)

    return sorted(categories, key=_key)
