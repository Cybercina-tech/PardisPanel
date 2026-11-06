"""Ownership helpers for Telegram hub admin APIs."""

from __future__ import annotations

from accounts.permissions import _normalize_role

from .models import TelegramBot


def user_is_super_admin(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _normalize_role(getattr(user, "role", None)) == "super_admin"


def user_is_management(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return _normalize_role(getattr(user, "role", None)) == "management"


def owned_bots_qs(user):
    """Bots owned by the given user."""
    return TelegramBot.objects.filter(owner=user)


def primary_owned_bot(user):
    """
    Prefer latest active owned bot; fall back to latest owned bot.

    Matches the spirit of ``telegram_bot_token_masked`` on ``/auth/me``.
    """
    qs = owned_bots_qs(user).order_by("-created_at")
    return qs.filter(is_active=True).first() or qs.first()


def bots_queryset_for_user(user):
    """
    Bots the user may work with on the Telegram page.

    Every signed-in panel user reaches every bot of their own desk, with no role
    or ownership gate on top: the account-scoped manager is the boundary, and it
    fails closed (super_admin runs unscoped and sees all).
    """
    return TelegramBot.objects.all()


def resolve_bot_for_user(user, bot_id=None):
    """
    Resolve the TelegramBot a hub request works on: the one asked for, else the
    user's own bot, else the desk's newest bot.

    Returns (bot, error_code, error_message).
    error_code is None on success.
    """
    bots = bots_queryset_for_user(user)
    if bot_id is not None:
        try:
            bot_id = int(bot_id)
        except (TypeError, ValueError):
            return None, "invalid_bot_id", "Invalid bot_id."
        bot = bots.filter(pk=bot_id).first()
        if bot is None:
            return None, "bot_not_found", "Bot not found."
        return bot, None, None

    bot = (
        primary_owned_bot(user)
        or bots.filter(is_active=True).order_by("-created_at").first()
        or bots.order_by("-created_at").first()
    )
    if bot is not None:
        return bot, None, None
    return None, "no_bot", "No bot token configured for this account."
