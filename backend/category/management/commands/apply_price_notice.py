"""Append the price notice to every stored Telegram description.

    python manage.py apply_price_notice [--dry-run]

Publishing already appends the notice when it sends (see
price_publisher.services.pardis_captions.with_price_notice); this writes it into
the stored category descriptions and template caption templates as well, so the
Telegram Studio editor and preview show exactly what customers receive. Empty
descriptions are left empty: they fall back to the built-in caption, which gets
the notice at send time. Safe to re-run.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from category.models import Category
from price_publisher.services.pardis_captions import PRICE_NOTICE, with_price_notice
from template_editor.models import Template


class Command(BaseCommand):
    help = "Append the price notice to stored Telegram descriptions and caption templates."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only, change nothing")

    def handle(self, *args, dry_run=False, **opts):
        changed = 0
        with transaction.atomic():
            for model, field in (
                (Category, "telegram_message_description"),
                (Template, "telegram_caption_template"),
            ):
                manager = getattr(model, "all_objects", model.objects)
                for obj in manager.all().order_by("pk"):
                    text = (getattr(obj, field) or "").strip()
                    if not text or PRICE_NOTICE in text:
                        continue
                    self.stdout.write(f"update: {model.__name__} #{obj.pk} {field}")
                    changed += 1
                    if not dry_run:
                        setattr(obj, field, with_price_notice(text))
                        obj.save(update_fields=[field])
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(f"{'dry run: ' if dry_run else ''}{changed} row(s) {'would change' if dry_run else 'updated'}")
