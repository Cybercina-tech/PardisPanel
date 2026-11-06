"""
Latest prices snapshot for public JSON API and outbound webhooks.
"""
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone

from category.models import Category, PriceType
from change_price.prefetch_helpers import prefetch_price_histories_latest
from special_price.models import SpecialPriceHistory, SpecialPricePair, SpecialPriceType


def _iso(dt):
    if dt is None:
        return None
    try:
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return timezone.localtime(dt).isoformat()
    except Exception:
        return None


def _money(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def _currency_mini(c):
    if c is None:
        return None
    return {"code": c.code, "name": c.name, "symbol": c.symbol or ""}


def build_prices_public_snapshot(finalized_only=False):
    """
    Return a JSON-serializable dict: categories with price types and latest history,
    plus special price types with per-pair latest history.

    ``finalized_only=True`` reports only prices that went through the finalize
    pipeline. The public website uses it so a rate reaches visitors when a
    manager finalizes it and not a keystroke earlier; the existing price feed
    and webhook keep the default and are unchanged.
    """
    now = timezone.now()
    categories = (
        Category.objects.all()
        .order_by("name")
        .prefetch_related(
            Prefetch(
                "price_types",
                queryset=(
                    PriceType.objects.select_related("source_currency", "target_currency")
                    .order_by("order", "id")
                    .prefetch_related(prefetch_price_histories_latest(finalized_only))
                ),
            )
        )
    )

    categories_out = []
    for cat in categories:
        pts_out = []
        for pt in cat.price_types.all():
            latest = pt.price_histories.first()
            eff = None
            if latest:
                eff = latest.event_at or latest.created_at
            pts_out.append(
                {
                    "id": pt.id,
                    "name": pt.name,
                    "slug": pt.slug,
                    "trade_type": pt.trade_type,
                    "is_active": pt.is_active,
                    "source_currency": _currency_mini(pt.source_currency),
                    "target_currency": _currency_mini(pt.target_currency),
                    "latest_price": _money(latest.price) if latest else None,
                    "latest_price_created_at": _iso(latest.created_at) if latest else None,
                    "latest_price_event_at": _iso(latest.event_at) if latest else None,
                    "latest_price_effective_at": _iso(eff) if eff else None,
                    "notes": (latest.notes or "") if latest else None,
                }
            )
        categories_out.append(
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "price_types": pts_out,
            }
        )

    pair_histories_qs = SpecialPriceHistory.objects.defer("event_at").order_by("-created_at")
    if finalized_only:
        pair_histories_qs = pair_histories_qs.filter(finalizations__isnull=False).distinct()
    special_types = (
        SpecialPriceType.objects.all()
        .order_by("name")
        .select_related("source_currency", "target_currency")
        .prefetch_related(
            Prefetch(
                "pairs",
                queryset=(
                    SpecialPricePair.objects.select_related("source_currency", "target_currency")
                    .order_by("id")
                    .prefetch_related(
                        Prefetch("histories", queryset=pair_histories_qs),
                    )
                ),
            )
        )
    )

    special_out = []
    for spt in special_types:
        pairs_data = []
        for pair in spt.pairs.all():
            hist = pair.histories.first()
            eff = None
            if hist:
                eff = hist.event_at or hist.created_at
            pairs_data.append(
                {
                    "id": pair.id,
                    "name": pair.name,
                    "trade_type": pair.trade_type,
                    "source_currency": _currency_mini(pair.source_currency),
                    "target_currency": _currency_mini(pair.target_currency),
                    "latest_price": _money(hist.price) if hist else None,
                    "latest_price_created_at": _iso(hist.created_at) if hist else None,
                    "latest_price_event_at": _iso(hist.event_at) if hist else None,
                    "latest_price_effective_at": _iso(eff) if eff else None,
                    "notes": (hist.notes or "") if hist else None,
                }
            )
        special_out.append(
            {
                "id": spt.id,
                "name": spt.name,
                "slug": spt.slug,
                "trade_type": spt.trade_type,
                "source_currency": _currency_mini(spt.source_currency),
                "target_currency": _currency_mini(spt.target_currency),
                "pairs": pairs_data,
            }
        )

    return {
        "generated_at": _iso(now),
        "categories": categories_out,
        "special_prices": special_out,
    }
