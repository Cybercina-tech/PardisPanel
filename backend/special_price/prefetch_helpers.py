"""Same idea as change_price.prefetch_helpers — optional columns omitted from SELECT."""
from django.db.models import Prefetch

from .models import SpecialPriceHistory


def prefetch_special_price_histories_latest():
    return Prefetch(
        "special_price_histories",
        queryset=SpecialPriceHistory.objects.defer("event_at").order_by("-created_at"),
    )
