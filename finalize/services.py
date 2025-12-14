"""
Service for sending finalized prices to external API.
Based on the data.py reference file.
"""
import logging
import os
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# API Configuration - Security: Use environment variables for sensitive data
EXTERNAL_API_URL = os.environ.get(
    'EXTERNAL_API_URL',
    "https://sarafipardis.co.uk/wp-json/pardis/v1/rates"
)
# Security: API key should be set via EXTERNAL_API_KEY environment variable
# Fallback to old value for backward compatibility (should be removed after migration)
EXTERNAL_API_KEY = os.environ.get(
    'EXTERNAL_API_KEY',
    "PX9k7mN2qR8vL4jH6wE3tY1uI5oP0aS9dF7gK2mN8xZ4cV6bQ1wE3rT5yU8iO0pL"
)

# The four keys we always want to handle (like data.py’s GBP/USDT helpers)
RATE_KEYS = ("GBP_BUY", "GBP_SELL", "USDT_BUY", "USDT_SELL")


class ExternalAPIService:
    """
    Service to send price updates to external API.
    Handles GBP and USDT prices (buy/sell) similar to data.py functions.
    """
    
    @staticmethod
    def send_request(currency: str, rate: float):
        """
        رفتار مطابق data.py:
        POST به همان URL با بدنه:
        {"currency": "<CODE>", "rate": <float>, "api_key": "<KEY>"}.
        """
        payload = {
            "currency": currency,
            "rate": float(rate),
            "api_key": EXTERNAL_API_KEY,
        }
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                EXTERNAL_API_URL,
                json=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            # بعضی نسخه‌ها چیزی برنمی‌گردانند، پس json لازم نیست حتماً باشد
            try:
                result = response.json()
            except ValueError:
                result = {"raw": response.text}
            logger.info(f"Successfully sent {currency} rate: {rate}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending {currency} rate {rate}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending {currency}: {e}")
            return None

    # -------- Helpers for reading existing rates (برای fallback) --------
    @staticmethod
    def get_existing_rates() -> dict | None:
        """
        Read current rates from external API, e.g.:
        {"GBP_BUY":65000,"GBP_SELL":67000,"USDT_BUY":42000,"USDT_SELL":43000}
        """
        try:
            response = requests.get(EXTERNAL_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                logger.warning(
                    "External API returned non-dict payload for GET /rates: %s", data
                )
                return None
            # Ensure only our known keys, castable to float
            cleaned: dict[str, float] = {}
            for key in RATE_KEYS:
                if key in data:
                    try:
                        cleaned[key] = float(data[key])
                    except (TypeError, ValueError):
                        logger.warning(
                            "External API returned non-numeric value for %s: %r",
                            key,
                            data[key],
                        )
            return cleaned or None
        except requests.exceptions.RequestException as exc:
            logger.error(f"Error fetching existing rates from external API: {exc}")
            return None
        except Exception as exc:  # defensive
            logger.error(f"Unexpected error fetching existing rates: {exc}")
            return None

    @staticmethod
    def send_rates_payload(rates: dict):
        """
        Send all GBP / USDT rates in a single payload.
        Always sends 4 keys (GBP_BUY, GBP_SELL, USDT_BUY, USDT_SELL):
        - اگر برای یک کلید قیمت جدید داریم: همان را می‌فرستیم
        - اگر نداریم، مقدار قبلی را از API می‌خوانیم
        - اگر هیچ مقداری وجود نداشته باشد، آن کلید را با مقدار 0 می‌فرستیم
        """
        # Get previous values from external API
        existing = ExternalAPIService.get_existing_rates() or {}

        full_rates: dict[str, float] = {}
        for key in RATE_KEYS:
            if key in rates:
                full_rates[key] = float(rates[key])
            elif key in existing:
                full_rates[key] = float(existing[key])
            else:
                # No new or previous value → fall back to 0
                full_rates[key] = 0.0

        headers = {"Content-Type": "application/json"}

        # مطابق data.py برای هر کلید یک درخواست جداگانه بفرستیم
        results = {"sent": [], "failed": []}
        for key, value in full_rates.items():
            resp = ExternalAPIService.send_request(key, value)
            if resp is not None:
                results["sent"].append(
                    {"currency": key, "rate": value, "response": resp}
                )
            else:
                results["failed"].append({"currency": key, "rate": value})

        return results

    @staticmethod
    def _build_rates_from_items(items):
        """
        Build a dict of rates (GBP_BUY / GBP_SELL / USDT_BUY / USDT_SELL)
        from a list of (price_type, price_history) tuples.
        """
        rates = {}
        skipped = []

        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                price_type, price_history = item
            else:
                skipped.append(str(item))
                logger.warning(f"Unknown price item format: {item}")
                continue

            try:
                source_code = (
                    getattr(price_type.source_currency, "code", "") or ""
                ).upper()
                target_code = (
                    getattr(price_type.target_currency, "code", "") or ""
                ).upper()
                trade_type = (getattr(price_type, "trade_type", "") or "").lower()
                price_value = float(getattr(price_history, "price", 0))
            except Exception as exc:  # defensive
                logger.warning(f"Failed to extract price data from item {item}: {exc}")
                skipped.append(str(item))
                continue

            key = None

            # Main mapping: GBP / IRR and USDT / IRR
            pair = {source_code, target_code}

            if pair == {"GBP", "IRR"} or pair == {"GBP", "IRT"}:
                # چه GBP/IRR باشد چه IRR/GBP، فقط نوع معامله برای BUY/SELL مهم است
                key = "GBP_BUY" if trade_type == "buy" else "GBP_SELL"
            elif pair == {"USDT", "IRR"} or pair == {"USDT", "IRT"}:
                # چه USDT/IRR باشد چه IRR/USDT، فقط نوع معامله برای BUY/SELL مهم است
                key = "USDT_BUY" if trade_type == "buy" else "USDT_SELL"

            if not key:
                skipped.append(f"{source_code}/{target_code} {trade_type}")
                continue

            # Latest value wins if there are duplicates
            rates[key] = price_value

        return rates, skipped
    
    @staticmethod
    def send_gbp_buy(rate):
        """Send GBP buy rate to external API."""
        return ExternalAPIService.send_request("GBP_BUY", rate)
    
    @staticmethod
    def send_gbp_sell(rate):
        """Send GBP sell rate to external API."""
        return ExternalAPIService.send_request("GBP_SELL", rate)
    
    @staticmethod
    def send_usdt_buy(rate):
        """Send USDT buy rate to external API."""
        return ExternalAPIService.send_request("USDT_BUY", rate)
    
    @staticmethod
    def send_usdt_sell(rate):
        """Send USDT sell rate to external API."""
        return ExternalAPIService.send_request("USDT_SELL", rate)
    
    @staticmethod
    def send_finalized_prices(price_items):
        """
        Send finalized prices to external API.
        Only sends GBP and USDT prices (buy/sell).
        
        Args:
            price_items: List of tuples (price_type, price_history) or (special_price_type, special_price_history)
        
        Returns:
            dict: Summary of sent prices with success/failure status.
                  Structure kept compatible with existing callers.
        """
        rates, skipped = ExternalAPIService._build_rates_from_items(price_items)

        results = {
            "sent": [],
            "failed": [],
            "skipped": skipped,
        }

        if not rates:
            logger.info("No GBP/USDT prices found in finalized items to send.")
            return results

        api_result = ExternalAPIService.send_rates_payload(rates)

        if api_result is not None:
            results["sent"].append(
                {
                    "payload": rates,
                    "response": api_result,
                }
            )
        else:
            results["failed"].append({"payload": rates})

        return results
    
    @staticmethod
    def send_finalized_special_prices(special_price_items):
        """
        Send finalized special prices to external API.
        Only sends GBP and USDT prices (buy/sell).
        
        Args:
            special_price_items: List of tuples (special_price_type, special_price_history)
        
        Returns:
            dict: Summary of sent prices with success/failure status
        """
        rates, skipped = ExternalAPIService._build_rates_from_items(
            special_price_items
        )

        results = {
            "sent": [],
            "failed": [],
            "skipped": skipped,
        }

        if not rates:
            logger.info("No GBP/USDT special prices found to send.")
            return results

        api_result = ExternalAPIService.send_rates_payload(rates)

        if api_result is not None:
            results["sent"].append(
                {
                    "payload": rates,
                    "response": api_result,
                }
            )
        else:
            results["failed"].append({"payload": rates})

        return results

