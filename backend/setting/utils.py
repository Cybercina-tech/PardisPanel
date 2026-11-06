"""
Utility functions for logging application events.
"""
import json
import logging

from .models import Log

logger = logging.getLogger(__name__)


def _serialize_details(details):
    """Normalize details for DB: dict -> JSON string; str/None unchanged."""
    if details is None:
        return None
    if isinstance(details, dict):
        return json.dumps(details, ensure_ascii=False, default=str)
    return details


def log_event(level='INFO', source='system', message='', details=None, user=None):
    """
    Create a log entry in the database.

    ``details`` may be a str or a dict (stored as JSON for structured logs).
    """
    return Log.objects.create(
        level=level,
        source=source,
        message=message,
        details=_serialize_details(details),
        user=user,
    )


def log_structured(
    level='INFO',
    source='system',
    message='',
    *,
    event=None,
    user=None,
    **fields,
):
    """
    Persist a structured log row: ``details`` is JSON ``{ "event": ..., ... }``.
    """
    payload = {}
    if event is not None:
        payload['event'] = event
    for key, value in fields.items():
        if value is not None:
            payload[key] = value
    details = payload if payload else None
    return log_event(
        level=level,
        source=source,
        message=message,
        details=details,
        user=user,
    )


def log_telegram_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Telegram events."""
    return log_event(level=level, source='telegram', message=message, details=details, user=user)


def log_finalize_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Finalize events."""
    return log_event(level=level, source='finalize', message=message, details=details, user=user)


def log_price_publisher_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Price Publisher events."""
    return log_event(level=level, source='price_publisher', message=message, details=details, user=user)


def log_template_editor_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Template Editor events."""
    return log_event(level=level, source='template_editor', message=message, details=details, user=user)


def read_auto_post_on_update_safe():
    """
    Read ``SiteSettings.auto_post_on_update`` without raising when the DB cannot
    satisfy a full ORM load (e.g. pending ``migrate`` on ``setting``).

    Returns dict: ``value`` (bool), ``ok`` (bool), ``detail`` (str|None).
    """
    from django.db import DatabaseError

    from setting.models import SiteSettings

    try:
        settings = SiteSettings.load()
        return {
            "value": bool(getattr(settings, "auto_post_on_update", False)),
            "ok": True,
            "detail": None,
        }
    except DatabaseError as exc:
        logger.exception(
            "read_auto_post_on_update_safe: SiteSettings unreadable (run migrations?): %s",
            exc,
        )
        return {
            "value": False,
            "ok": False,
            "detail": (
                "Site settings database schema is out of date. "
                "Run: python manage.py migrate setting"
            ),
        }


def write_auto_post_on_update_safe(value):
    """
    Persist ``auto_post_on_update``. Same resilience as read_auto_post_on_update_safe.

    Returns dict: ``ok`` (bool), ``detail`` (str|None).
    """
    from django.db import DatabaseError

    from setting.models import SiteSettings

    try:
        settings = SiteSettings.load()
        settings.auto_post_on_update = bool(value)
        settings.save()
        return {"ok": True, "detail": None}
    except DatabaseError as exc:
        logger.exception(
            "write_auto_post_on_update_safe: SiteSettings save failed (run migrations?): %s",
            exc,
        )
        return {
            "ok": False,
            "detail": (
                "Site settings database schema is out of date. "
                "Run: python manage.py migrate setting"
            ),
        }
