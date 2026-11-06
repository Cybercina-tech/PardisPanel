import logging
from typing import Optional

from celery import shared_task

from accounts.scoping import act_as_account

from category.models import Category
from change_price.models import PriceHistory
from finalize.models import Finalization, SpecialPriceFinalization
from price_publisher.services.publisher import PricePublicationError, PricePublisherService
from special_price.models import SpecialPriceHistory
from telegram_app.models import TelegramChannel

logger = logging.getLogger(__name__)


def _already_published_category(channel_id: int, price_history_ids: list[int]) -> bool:
    if not price_history_ids:
        return False
    price_history_ids = sorted(set(price_history_ids))
    expected_count = len(price_history_ids)
    candidates = Finalization.objects.filter(
        channel_id=channel_id,
        message_sent=True,
    ).order_by("-finalized_at")[:20]
    for finalization in candidates:
        finalized_ids = sorted(
            finalization.finalized_prices.values_list("price_history_id", flat=True)
        )
        if finalized_ids == price_history_ids:
            return True
        if len(finalized_ids) < expected_count:
            break
    return False


@shared_task(
    bind=True,
    autoretry_for=(),
    retry_backoff=False,
    retry_jitter=False,
)
def publish_category_prices_task(
    self,
    *,
    category_id: int,
    channel_id: int,
    notes: Optional[str],
    price_history_ids: list[int],
    user_id: Optional[int] = None,
):
    """
    Render + publish category prices to Telegram in worker process.
    Returns a dict that mirrors PublicationResult fields.
    """
    if _already_published_category(channel_id=channel_id, price_history_ids=price_history_ids):
        return {
            "success": True,
            "response": "Skipped duplicate category publication (already published).",
            "caption": None,
            "publish_path": "idempotent_skip",
            "render_fallback_reason": None,
        }

    category = Category.objects.get(id=category_id)
    channel = TelegramChannel.objects.select_related("bot").get(id=channel_id, is_active=True)

    with act_as_account(category.account_id):
        return _publish_category(category, channel, price_history_ids, notes, user_id)


def _publish_category(category, channel, price_history_ids, notes, user_id):
    category_id = category.pk

    histories = (
        PriceHistory.objects.filter(id__in=price_history_ids, price_type__category_id=category_id)
        .select_related(
            "price_type",
            "price_type__source_currency",
            "price_type__target_currency",
        )
        .order_by("id")
    )
    price_items = [(ph.price_type, ph) for ph in histories]

    if not price_items:
        raise PricePublicationError("No price entries were provided for publication.")

    acting_user = None
    if user_id:
        from accounts.models import CustomUser

        acting_user = CustomUser.objects.filter(pk=user_id).first()

    try:
        publication = PricePublisherService(acting_user=acting_user).publish_category_prices(
            category=category,
            price_items=price_items,
            channel=channel,
            notes=notes,
        )
    except PricePublicationError as exc:
        return {
            "success": False,
            "response": str(exc),
            "caption": None,
            "publish_path": "template_contract_error",
            "render_fallback_reason": "template_missing_or_invalid",
        }
    return {
        "success": publication.success,
        "response": publication.response,
        "caption": publication.caption,
        "template_id": publication.template_id,
        "publish_path": publication.publish_path,
        "render_fallback_reason": publication.render_fallback_reason,
    }


@shared_task(
    bind=True,
    autoretry_for=(),
    retry_backoff=False,
    retry_jitter=False,
)
def publish_special_price_task(
    self,
    *,
    special_price_history_id: int,
    channel_id: int,
    notes: Optional[str],
    user_id: Optional[int] = None,
):
    """
    Render + publish special price to Telegram in worker process.
    Returns a dict that mirrors PublicationResult fields.
    """
    existing = SpecialPriceFinalization.objects.filter(
        special_price_history_id=special_price_history_id,
        channel_id=channel_id,
        message_sent=True,
    ).exists()
    if existing:
        return {
            "success": True,
            "response": "Skipped duplicate special publication (already published).",
            "caption": None,
            "publish_path": "idempotent_skip",
            "render_fallback_reason": None,
        }

    special_price_history = SpecialPriceHistory.objects.select_related(
        "special_price_type",
        "special_price_type__source_currency",
        "special_price_type__target_currency",
    ).get(id=special_price_history_id)
    channel = TelegramChannel.objects.select_related("bot").get(id=channel_id, is_active=True)

    with act_as_account(special_price_history.special_price_type.account_id):
        return _publish_special(special_price_history, channel, notes, user_id)


def _publish_special(special_price_history, channel, notes, user_id):

    acting_user = None
    if user_id:
        from accounts.models import CustomUser

        acting_user = CustomUser.objects.filter(pk=user_id).first()

    publication = PricePublisherService(acting_user=acting_user).publish_special_price(
        special_price_type=special_price_history.special_price_type,
        price_history=special_price_history,
        channel=channel,
        notes=notes,
    )
    return {
        "success": publication.success,
        "response": publication.response,
        "caption": publication.caption,
        "template_id": publication.template_id,
        "publish_path": publication.publish_path,
        "render_fallback_reason": publication.render_fallback_reason,
    }
