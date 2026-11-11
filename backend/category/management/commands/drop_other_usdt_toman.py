"""Delete the Tether/Toman buy and sell price types from the "Other currencies" category.

    python manage.py drop_other_usdt_toman [--dry-run]

The Other-currencies banner never shows USDT against Toman, so those two types are
removed together with their price history, finalize records and template bindings.
Types in any other category, and USDT/GBP, are left alone.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from category.models import PriceType
from change_price.models import PriceHistory

OTHER_CATEGORY_MARK = "سایر"
TOMAN_CODES = ("IRR", "IRT")


class Command(BaseCommand):
    help = "Delete USDT/Toman price types from the Other-currencies category."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only, change nothing")

    def handle(self, *args, dry_run=False, **opts):
        types = list(
            PriceType.all_objects.filter(
                Q(source_currency__code="USDT", target_currency__code__in=TOMAN_CODES)
                | Q(target_currency__code="USDT", source_currency__code__in=TOMAN_CODES),
                category__name__contains=OTHER_CATEGORY_MARK,
            )
            .select_related("category")
            .order_by("id")
        )
        if not types:
            self.stdout.write("no USDT/Toman price type in an Other-currencies category")
            return

        with transaction.atomic():
            for t in types:
                n = PriceHistory.all_objects.filter(price_type=t).count()
                self.stdout.write(f"remove: #{t.id} {t.name!r} in {t.category.name!r} ({n} history rows)")
                if not dry_run:
                    t.delete()
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write("dry run: nothing changed" if dry_run else "done")
