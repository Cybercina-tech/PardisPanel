"""
Service for sending finalized prices to external API.
Sends exactly four rates: GBP_BUY, GBP_SELL, USDT_BUY, USDT_SELL.
Uses values from price_items directly — no DB read, no API fetch.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

RATE_KEYS = ("GBP_BUY", "GBP_SELL", "USDT_BUY", "USDT_SELL")
TIMEOUT_SECONDS = 10


def _build_rates_from_items(price_items):
    """
    Extract rates from (price_type, price_history) tuples.
    Only accepts:
    - GBP: pair {GBP, IRR} or {GBP, IRT}, price_type.name contains "حسابی" OR "account"
    - USDT: pair {USDT, IRR} or {USDT, IRT} (NOT USDT/GBP)
    """
    rates = {}
    skipped = []

    logger.info("_build_rates_from_items: processing %d items", len(price_items))

    for i, item in enumerate(price_items):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            skipped.append(f"Invalid item format: {item}")
            continue

        price_type, price_history = item

        try:
            source_code = (getattr(price_type.source_currency, "code", "") or "").strip().upper()
            target_code = (getattr(price_type.target_currency, "code", "") or "").strip().upper()
            trade_type = (getattr(price_type, "trade_type", "") or "").strip().lower()
            price_type_name = (getattr(price_type, "name", "") or "").strip().lower()

            price_attr = getattr(price_history, "price", None)
            price_value = float(price_attr) if price_attr is not None else 0.0

            logger.info(
                "  [%d] name='%s' pair=%s/%s trade=%s price=%s",
                i, price_type_name, source_code, target_code, trade_type, price_value,
            )

            if trade_type not in ("buy", "sell"):
                skipped.append(f"Invalid trade_type: {trade_type}")
                continue

            pair = {source_code, target_code}

            # USDT/GBP: NEVER use — only USDT/IRR (تتر به تومان) is sent
            if pair == {'USDT', 'GBP'}:
                skipped.append(
                    f"USDT/GBP skipped (only USDT/IRR sent): {source_code}/{target_code} {trade_type}={price_value}"
                )
                continue

            if pair in ({'GBP', 'IRR'}, {'GBP', 'IRT'}):
                is_account = (
                    "حسابی" in price_type_name
                    or "از حساب" in price_type_name
                    or "account" in price_type_name
                )
                if not is_account:
                    skipped.append(f"GBP cash skipped (need account): {source_code}/{target_code} {trade_type}")
                    continue
                key = "GBP_BUY" if trade_type == "buy" else "GBP_SELL"

            elif pair in ({'USDT', 'IRR'}, {'USDT', 'IRT'}):
                # Skip items whose name indicates GBP/pound (misconfigured pair)
                if "پوند" in price_type_name or "gbp" in price_type_name or "pound" in price_type_name:
                    skipped.append(
                        f"USDT item name contains pound/gbp, skipped: "
                        f"name='{price_type_name}' {source_code}/{target_code} {trade_type}={price_value}"
                    )
                    continue
                key = "USDT_BUY" if trade_type == "buy" else "USDT_SELL"

            else:
                skipped.append(f"Pair not accepted: {source_code}/{target_code}")
                continue

            rates[key] = price_value
            logger.info("Extracted %s = %s from %s/%s %s", key, price_value, source_code, target_code, trade_type)

        except Exception as exc:
            logger.warning("Failed to extract from item: %s", exc, exc_info=True)
            skipped.append(f"Extract error: {exc}")

    return rates, skipped


def _send_one_rate(currency: str, rate: float) -> bool:
    """
    Send one rate via POST. Returns True on success, False on failure.
    """
    api_url = getattr(settings, "EXTERNAL_API_URL", None)
    api_key = getattr(settings, "EXTERNAL_API_KEY", None)

    if not api_url or not api_key:
        logger.error("EXTERNAL_API_URL or EXTERNAL_API_KEY not configured in settings")
        return False

    payload = {"currency": currency, "rate": float(rate), "api_key": api_key}
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=TIMEOUT_SECONDS)

        if resp.status_code != 200:
            logger.error(
                "External API returned status %s for %s=%s. Body: %s",
                resp.status_code, currency, rate, resp.text
            )
            return False

        logger.info("Sent %s = %s successfully", currency, rate)
        return True

    except requests.exceptions.RequestException as exc:
        logger.exception("Request failed for %s=%s: %s", currency, rate, exc)
        return False
    except Exception as exc:
        logger.exception("Unexpected error sending %s=%s: %s", currency, rate, exc)
        return False


class ExternalAPIService:
    """Sends finalized prices to external API. Uses price_items values only."""

    @classmethod
    def send_finalized_prices(cls, price_items):
        """
        Build rates from price_items and send each to the API.
        No DB read. No API fetch. No merging. No fallback.
        """
        if not price_items:
            logger.info("send_finalized_prices called with empty price_items")
            return {"sent": [], "failed": [], "skipped": []}

        rates, skipped = _build_rates_from_items(price_items)

        if not rates:
            logger.info("No GBP/USDT rates extracted. Skipped: %s", skipped)
            return {"sent": [], "failed": [], "skipped": skipped}

        logger.info("Rates to send: %s", rates)

        sent = []
        failed = []

        for key in RATE_KEYS:
            if key not in rates:
                continue
            value = rates[key]
            ok = _send_one_rate(key, value)
            if ok:
                sent.append({"currency": key, "rate": value})
            else:
                failed.append({"currency": key, "rate": value})

        logger.info("External API: %d sent, %d failed", len(sent), len(failed))
        return {"sent": sent, "failed": failed, "skipped": skipped}

    @classmethod
    def send_finalized_special_prices(cls, special_price_items):
        """Same as send_finalized_prices; special_price_items use same (type, history) structure."""
        return cls.send_finalized_prices(special_price_items)
