import logging
import threading

import requests

from core.prices_snapshot import build_prices_public_snapshot
from setting.models import SiteSettings

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SEC = 8


def notify_prices_webhook(source: str) -> None:
    """
    If SiteSettings.prices_webhook_url is set, POST JSON {event, source, prices} in a daemon thread.
    Never raises to callers; logs failures.
    """
    try:
        site = SiteSettings.load()
    except Exception:
        logger.exception("prices_webhook: could not load SiteSettings")
        return

    url = (getattr(site, "prices_webhook_url", None) or "").strip()
    if not url:
        return

    try:
        prices = build_prices_public_snapshot()
    except Exception:
        logger.exception("prices_webhook: snapshot failed (source=%s)", source)
        return

    payload = {
        "event": "prices_updated",
        "source": source,
        "prices": prices,
    }

    def _post():
        try:
            requests.post(
                url,
                json=payload,
                timeout=WEBHOOK_TIMEOUT_SEC,
                headers={"Content-Type": "application/json"},
            )
        except requests.RequestException as exc:
            logger.warning("prices_webhook POST failed (source=%s): %s", source, exc)

    threading.Thread(target=_post, daemon=True).start()
