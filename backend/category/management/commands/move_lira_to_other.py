"""Keep the lira (TRY) price type only in the "Other currencies" category.

    python manage.py move_lira_to_other [--dry-run]

Pardis carried a second lira price type under Pound. The lira belongs to the
Other-currencies board (right below the dirham), so any TRY type outside it is
removed together with its history. The type that stays is the one in a category
whose name contains "سایر"; if none matches, the one with the newest price.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from category.models import PriceType

OTHER_CATEGORY_MARK = "سایر"


class Command(BaseCommand):
    help = "Keep the TRY price type only in the Other-currencies category."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only, change nothing")

    def handle(self, *args, dry_run=False, **opts):
        types = list(
            PriceType._base_manager.filter(Q(source_currency__code="TRY") | Q(target_currency__code="TRY"))
            .select_related("category")
            .order_by("category_id", "id")
        )
        if not types:
            self.stdout.write("no lira price type found")
            return

        def latest(pt):
            row = pt.price_histories.order_by("-created_at", "-id").first()
            return row.created_at if row else None

        keep = next((t for t in types if OTHER_CATEGORY_MARK in (t.category.name or "")), None)
        if keep is None:
            dated = [(latest(t), t) for t in types if latest(t)]
            if not dated:
                raise CommandError("no lira type sits in an Other-currencies category and none has a price")
            keep = max(dated, key=lambda d: d[0])[1]

        self.stdout.write(f"keep: #{keep.id} {keep.name!r} in {keep.category.name!r}")
        drop = [t for t in types if t.pk != keep.pk]
        with transaction.atomic():
            for t in drop:
                n = t.price_histories.count()
                self.stdout.write(f"remove: #{t.id} {t.name!r} in {t.category.name!r} ({n} history rows)")
                if not dry_run:
                    t.delete()
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write("dry run: nothing changed" if dry_run else "done")
