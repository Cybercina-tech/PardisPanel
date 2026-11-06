"""Endpoints whose URL and JSON shape belong to the original Pardis panel.

Third-party sites read ``GET /prices/live-json/`` without credentials, so its
path, field names, ordering and value formats must never change.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.scoping import act_as_account, resolve_public_account_id, unscoped
from category.models import PriceType


@require_GET
def live_prices_json(request):
    with unscoped():
        account_id = resolve_public_account_id(request.GET.get("account"))
    with act_as_account(account_id):
        # Pardis ordered price types by name; SE orders by (order, id). Keep the
        # Pardis order explicit so consumers that index by position keep working.
        price_types = (
            PriceType.objects.select_related("category", "source_currency", "target_currency")
            .prefetch_related("price_histories")
            .order_by("name")
        )
        prices = []
        for price_type in price_types:
            latest = price_type.price_histories.first()
            prices.append(
                {
                    "category_name": price_type.category.slug,
                    "price_type_name": price_type.slug,
                    "trade_type": price_type.trade_type,
                    "source_currency": price_type.source_currency.code,
                    "target_currency": price_type.target_currency.code,
                    "latest_price": str(latest.price) if latest is not None else None,
                    "updated_at": latest.updated_at.isoformat() if latest is not None else None,
                }
            )
    return JsonResponse({"count": len(prices), "prices": prices})
