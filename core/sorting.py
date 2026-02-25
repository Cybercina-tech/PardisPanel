"""
Shared sorting utilities for price types and categories.
Single source of truth -- replaces duplicates in change_price/views,
finalize/views, and change_price/templatetags.
"""
from __future__ import annotations

from typing import Iterable


def sort_gbp_price_types(price_types):
    """
    Sort price types for GBP/Pound category:
    1. خرید از حساب (Buy Account)
    2. خرید نقدی (Buy Cash)
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
            if "حساب" in name or "account" in name_lower:
                return 1
            if "نقدی" in name or "نقد" in name or "cash" in name_lower:
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

        if trade_type == "buy":
            if has_toman:
                return 1
            if has_gbp:
                return 3
            return 10
        if trade_type == "sell":
            if has_toman:
                return 2
            if has_gbp:
                return 4
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
