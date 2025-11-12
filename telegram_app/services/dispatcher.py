import logging
from dataclasses import dataclass
from typing import List

from ..models import DefaultMessageSettings
from .telegram_client import TelegramService

logger = logging.getLogger(__name__)


@dataclass
class DispatchResult:
    bot: str
    channel: str
    success: bool
    detail: str
    fallback_used: bool = False


def _prepare_caption(settings: DefaultMessageSettings, template_name: str) -> str:
    caption = (settings.default_caption or "").strip()
    if caption:
        return caption
    return f"🔔 {template_name}"


def broadcast_rendered_template(
    template,
    image_path: str,
    image_url: str | None = None,
) -> List[dict]:
    """
    Broadcast a rendered template image to all active channels for bots with active settings.

    Returns a list of dispatch results dictionaries.
    """
    results: List[DispatchResult] = []

    active_settings = (
        DefaultMessageSettings.objects.select_related("bot")
        .prefetch_related("bot__channels")
        .filter(active=True, bot__is_active=True)
    )

    for settings in active_settings:
        bot = settings.bot
        channels = bot.channels.filter(is_active=True)
        if not channels.exists():
            logger.info(
                "No active channels found for bot '%s'; skipping broadcast.",
                bot,
            )
            continue

        caption = _prepare_caption(settings, template.name)
        buttons = settings.default_buttons or []

        try:
            client = TelegramService(bot.token)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to initialize Telegram client for bot '%s': %s", bot, exc)
            continue

        for channel in channels:
            success = False
            detail = ""
            fallback_used = False

            try:
                success, detail = client.send_photo(
                    chat_id=channel.chat_id,
                    photo=image_path,
                    caption=caption,
                    buttons=buttons,
                )
                if not success:
                    fallback_used = True
                    success, detail = client.send_message(
                        chat_id=channel.chat_id,
                        text=caption,
                        buttons=buttons,
                    )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to send rendered template to '%s' via bot '%s': %s",
                    channel.chat_id,
                    bot,
                    exc,
                )
                success = False
                detail = str(exc)

            results.append(
                DispatchResult(
                    bot=str(bot),
                    channel=channel.chat_id,
                    success=success,
                    detail=detail,
                    fallback_used=fallback_used,
                )
            )

    return [
        {
            "bot": result.bot,
            "channel": result.channel,
            "success": result.success,
            "message": result.detail,
            "fallback_used": result.fallback_used,
            "image_url": image_url,
        }
        for result in results
    ]

