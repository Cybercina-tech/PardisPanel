"""
Management command to debug what rates would be sent to the external API.
Usage: python manage.py debug_rates
"""
import sys
import io
from django.core.management.base import BaseCommand
from category.models import Category, PriceType
from change_price.models import PriceHistory
from finalize.services import _build_rates_from_items
from django.conf import settings


class Command(BaseCommand):
    help = "Show all PriceTypes and what would be sent to external API"

    def handle(self, *args, **options):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        self.stdout = self.stdout.__class__(sys.stdout)
        self.stdout.write("\n=== EXTERNAL API SETTINGS ===")
        url = getattr(settings, "EXTERNAL_API_URL", "NOT SET")
        key = getattr(settings, "EXTERNAL_API_KEY", "")
        self.stdout.write(f"  URL: {url}")
        self.stdout.write(f"  KEY: {'SET (' + key[:8] + '...)' if key else 'EMPTY - THIS IS THE PROBLEM!'}")

        categories = Category.objects.all()
        for cat in categories:
            self.stdout.write(f"\n=== Category: {cat.name} (id={cat.id}) ===")
            price_types = PriceType.objects.filter(category=cat).select_related(
                "source_currency", "target_currency"
            )

            if not price_types.exists():
                self.stdout.write("  (no price types)")
                continue

            price_items = []
            for pt in price_types:
                latest = PriceHistory.objects.filter(price_type=pt).order_by("-created_at").first()
                src = pt.source_currency.code if pt.source_currency else "?"
                tgt = pt.target_currency.code if pt.target_currency else "?"
                price_val = latest.price if latest else "NO HISTORY"
                self.stdout.write(
                    f"  PriceType id={pt.id}: name='{pt.name}' "
                    f"pair={src}/{tgt} trade={pt.trade_type} "
                    f"latest_price={price_val}"
                )
                if latest:
                    price_items.append((pt, latest))

            if price_items:
                rates, skipped = _build_rates_from_items(price_items)
                self.stdout.write(f"\n  -> Extracted rates: {rates}")
                if skipped:
                    self.stdout.write(f"  -> Skipped: {skipped}")
                if not rates:
                    self.stdout.write(
                        self.style.WARNING("  -> NO rates would be sent for this category!")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("  -> No price history found for any PriceType")
                )

        self.stdout.write("\n=== DONE ===\n")
