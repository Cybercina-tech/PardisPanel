"""
Prefetch helpers so history queries do not SELECT optional columns (e.g. ``event_at``)
that may be missing on databases where migrations were not applied yet.
"""
from django.db.models import Prefetch

from .models import PriceHistory


def prefetch_price_histories_latest(finalized_only=False):
    """Latest-first price histories for PriceType.prefetch_related(...).

    ``finalized_only`` narrows to rows a manager has actually finalized, which
    is what anything customer-facing must use: a price typed into the panel but
    not yet approved is a draft, and publishing it would quote a rate the desk
    has not agreed to.
    """
    queryset = PriceHistory.objects.defer("event_at").order_by("-created_at")
    if finalized_only:
        queryset = queryset.filter(finalizations__isnull=False).distinct()
    return Prefetch("price_histories", queryset=queryset)
