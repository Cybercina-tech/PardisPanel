"""Give the Pardis account its name and logo (idempotent).

Called by ``import_pardis``; run it on its own to re-apply after a settings reset.
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from accounts.models import Account
from setting.models import SiteSettings

SITE_NAME = "Sarafi Pardis"
# Publish targets besides the @pardis_addon channel the panel was set up with.
MAIN_CHANNELS = [("Sarafi Pardis", "@sarafipardis")]
LOGO_SOURCE = Path(settings.BASE_DIR) / "static" / "img" / "sarafi-pardis-logo.png"


def apply_branding(account, *, replace_logo=False):
    site = SiteSettings.load(account=account)
    site.site_name = SITE_NAME
    if LOGO_SOURCE.is_file() and (replace_logo or not site.logo):
        with LOGO_SOURCE.open("rb") as fh:
            site.logo.save("sarafi-pardis-logo.png", File(fh), save=False)
    site.save()
    return site


def _category_buttons(rows):
    # ``row`` keeps the website and Instagram buttons side by side, as in Pardis.
    return [{"label": b["text"], "url": b["url"], "row": r} for r, row in enumerate(rows) for b in row]


def apply_telegram_content(account):
    """Fill every category's Telegram description and buttons with the Pardis defaults.

    Only empty fields are filled, so edits made in the Telegram editor are kept. Buttons
    still equal to the previous default (before the channel/bot row) are upgraded.
    Returns the number of categories changed.
    """
    from accounts.scoping import act_as_account
    from category.models import Category
    from price_publisher.services.legacy_category_renderer import supports_category
    from price_publisher.services.publisher import (
        LEGACY_FINAL_BUTTONS,
        LEGACY_FINAL_MESSAGE,
        TELEGRAM_LINKS_ROW,
    )
    from price_publisher.services.pardis_captions import GBP_CAPTION, TETHER_CAPTION
    from price_publisher.services.tether_renderer import supports_tether_category

    buttons = _category_buttons(LEGACY_FINAL_BUTTONS)
    previous_default = _category_buttons(
        [row for row in LEGACY_FINAL_BUTTONS if row is not TELEGRAM_LINKS_ROW]
    )
    changed = 0
    with act_as_account(account.pk):
        for category in Category.objects.all():
            if supports_tether_category(category):
                caption = TETHER_CAPTION
            elif supports_category(category):
                caption = GBP_CAPTION
            else:
                caption = LEGACY_FINAL_MESSAGE
            dirty = []
            if not (category.telegram_message_description or "").strip():
                category.telegram_message_description = caption
                dirty.append("telegram_message_description")
            if not category.inline_buttons or category.inline_buttons == previous_default:
                category.inline_buttons = buttons
                dirty.append("inline_buttons")
            if dirty:
                category.save(update_fields=dirty)
                changed += 1
    return changed


def ensure_main_channels(account):
    """Register the main Pardis channels on the bot the account already publishes with.

    Returns the chat ids added, or None when the account has no bot yet.
    The bot must be an admin of each channel to post there.
    """
    from accounts.scoping import act_as_account
    from telegram_app.models import TelegramBot, TelegramChannel

    added = []
    with act_as_account(account.pk):
        existing = TelegramChannel.objects.select_related("bot").order_by("created_at").first()
        bot = existing.bot if existing else TelegramBot.objects.filter(is_active=True).first()
        if bot is None:
            return None
        for name, chat_id in MAIN_CHANNELS:
            _, created = TelegramChannel.all_objects.get_or_create(
                bot=bot, chat_id=chat_id, defaults={"name": name, "is_active": True}
            )
            if created:
                added.append(chat_id)
    return added


class Command(BaseCommand):
    help = "Set the Pardis account's site name, logo and default Telegram content."

    def add_arguments(self, parser):
        parser.add_argument("--replace-logo", action="store_true")

    def handle(self, *args, replace_logo=False, **opts):
        account = Account.objects.filter(slug="pardis").first()
        if account is None:
            raise CommandError("No 'pardis' account; run import_pardis first.")
        apply_branding(account, replace_logo=replace_logo)
        n = apply_telegram_content(account)
        self.stdout.write(self.style.SUCCESS(f"Branding applied; Telegram content set on {n} categories."))
        added = ensure_main_channels(account)
        if added is None:
            self.stdout.write(self.style.WARNING("No Telegram bot for this account; main channel not added."))
        elif added:
            self.stdout.write(self.style.SUCCESS(f"Channels added: {', '.join(added)} (bot must be admin there)."))
