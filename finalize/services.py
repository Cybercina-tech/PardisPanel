"""
Service for sending finalized prices to external API.
Based on the data.py reference file.
"""
import json
import logging
import os
import requests
from django.conf import settings
from django.utils import timezone

from setting.utils import log_finalize_event

logger = logging.getLogger(__name__)

# Prefix for easy log filtering (e.g. grep "[ExternalAPI]")
_LOG_PREFIX = "[ExternalAPI]"

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
        ارسال قیمت به API خارجی - دقیقاً مطابق t.py:
        POST به URL با بدنه:
        {"currency": "<CODE>", "rate": <float>, "api_key": "<KEY>"}.
        """
        payload = {
            "currency": currency,
            "rate": float(rate),
            "api_key": EXTERNAL_API_KEY,
        }
        headers = {"Content-Type": "application/json"}

        # Instrumentation: full REQUEST payload (api_key masked in log for security)
        payload_log = {"currency": payload["currency"], "rate": payload["rate"], "api_key": "<REDACTED>"}
        logger.info(
            f"{_LOG_PREFIX} send_request REQUEST: url={EXTERNAL_API_URL} "
            f"payload={payload_log}"
        )

        try:
            response = requests.post(
                EXTERNAL_API_URL,
                json=payload,
                headers=headers,
                timeout=10,
            )

            # Instrumentation: full RESPONSE status and body
            logger.info(
                f"{_LOG_PREFIX} send_request RESPONSE: status={response.status_code} "
                f"headers={dict(response.headers)}"
            )

            response.raise_for_status()

            try:
                result = response.json()
                logger.info(f"{_LOG_PREFIX} send_request RESPONSE body (JSON): {result}")
            except ValueError:
                result = {"raw": response.text}
                logger.info(
                    f"{_LOG_PREFIX} send_request RESPONSE body (raw, first 500 chars): "
                    f"{response.text[:500]!r}"
                )

            logger.info(f"{_LOG_PREFIX} Successfully sent {currency} = {rate}")
            return result

        except requests.exceptions.Timeout as e:
            logger.error(
                f"{_LOG_PREFIX} Timeout sending {currency} = {rate}: {e} "
                f"(url={EXTERNAL_API_URL})"
            )
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"{_LOG_PREFIX} Connection error sending {currency} = {rate}: {e} "
                f"(url={EXTERNAL_API_URL})"
            )
            return None
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "N/A"
            body = (e.response.text[:500] if e.response else "N/A")
            logger.error(
                f"{_LOG_PREFIX} HTTP error sending {currency} = {rate}: {e} "
                f"status={status} body={body!r}"
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.error(
                f"{_LOG_PREFIX} Request error sending {currency} = {rate}: {e} "
                f"(url={EXTERNAL_API_URL})"
            )
            return None
        except Exception as e:
            logger.error(
                f"{_LOG_PREFIX} Unexpected error sending {currency}: {e}",
                exc_info=True,
            )
            return None

    # -------- Helpers for reading existing rates (برای fallback) --------
    @staticmethod
    def get_existing_rates() -> dict | None:
        """
        Read current rates from external API, e.g.:
        {"GBP_BUY":65000,"GBP_SELL":67000,"USDT_BUY":42000,"USDT_SELL":43000}
        """
        try:
            logger.info(f"{_LOG_PREFIX} get_existing_rates: GET {EXTERNAL_API_URL}")
            response = requests.get(EXTERNAL_API_URL, timeout=10)
            logger.info(
                f"{_LOG_PREFIX} get_existing_rates: response status={response.status_code}"
            )
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
            logger.info(f"{_LOG_PREFIX} get_existing_rates: parsed cleaned={cleaned}")
            return cleaned or None
        except requests.exceptions.RequestException as exc:
            logger.error(
                f"{_LOG_PREFIX} get_existing_rates: RequestException {exc} "
                f"(url={EXTERNAL_API_URL})"
            )
            return None
        except Exception as exc:  # defensive
            logger.error(f"Unexpected error fetching existing rates: {exc}")
            return None

    @staticmethod
    def send_rates_payload(rates: dict):
        """
        ارسال هر 4 قیمت به صورت جداگانه - دقیقاً مطابق t.py:
        همیشه هر 4 کلید (GBP_BUY, GBP_SELL, USDT_BUY, USDT_SELL) را می‌فرستد.
        - اگر برای یک کلید قیمت جدید داریم: همان را می‌فرستیم
        - اگر نداریم، مقدار قبلی را از API می‌خوانیم
        - اگر هیچ مقداری وجود نداشته باشد، آن کلید را با مقدار 0 می‌فرستیم
        
        هر قیمت به صورت جداگانه با یک درخواست POST ارسال می‌شود (مثل t.py).
        """
        # Get previous values from external API
        existing = ExternalAPIService.get_existing_rates() or {}
        logger.info(
            f"{_LOG_PREFIX} send_rates_payload: existing={existing} new_rates={rates}"
        )

        # همیشه هر 4 قیمت را آماده می‌کنیم
        full_rates: dict[str, float] = {}
        for key in RATE_KEYS:
            if key in rates:
                rate_value = float(rates[key])
                full_rates[key] = rate_value
                logger.info(
                    f"{_LOG_PREFIX} send_rates_payload: {key} using NEW rate={rate_value}"
                )
            elif key in existing:
                existing_value = float(existing[key])
                full_rates[key] = existing_value
                logger.info(
                    f"{_LOG_PREFIX} send_rates_payload: {key} using EXISTING "
                    f"from API={existing_value}"
                )
            else:
                full_rates[key] = 0.0
                logger.warning(
                    f"{_LOG_PREFIX} send_rates_payload: {key} no rate found, "
                    f"using 0.0"
                )

        # Special logging for USDT_SELL
        if "USDT_SELL" in full_rates:
            logger.info(
                f"USDT_SELL final value: {full_rates['USDT_SELL']}, "
                f"source: {'new' if 'USDT_SELL' in rates else 'existing' if 'USDT_SELL' in existing else 'default'}"
            )
        elif "USDT_SELL" not in full_rates:
            logger.error(
                f"USDT_SELL was not included in final rates! "
                f"New rates: {rates.get('USDT_SELL', 'N/A')}, "
                f"Existing rates: {existing.get('USDT_SELL', 'N/A')}"
            )

        # -------- SEEDED LOGGING: persist full_rates to Log BEFORE POST loop --------
        # Runs even if subsequent POSTs fail; use for troubleshooting data vs connection.
        try:
            ts = timezone.now().isoformat()
            details = f"rates={json.dumps(full_rates)} timestamp={ts}"
            log_finalize_event(
                level="INFO",
                message="SEED_LOG: API Rates Prepared",
                details=details,
                user=None,
            )
            logger.info(f"{_LOG_PREFIX} SEED_LOG written to Log: {details}")
        except Exception as exc:
            logger.error(
                f"{_LOG_PREFIX} Failed to write SEED_LOG to Log: {exc}",
                exc_info=True,
            )

        # ارسال هر 4 قیمت به صورت جداگانه
        logger.info(
            f"{_LOG_PREFIX} send_rates_payload: starting to POST {len(full_rates)} "
            f"rates to API: {full_rates}"
        )
        results = {"sent": [], "failed": []}

        for key, value in full_rates.items():
            logger.info(f"{_LOG_PREFIX} send_rates_payload: POST {key} = {value}")
            # ارسال هر قیمت به صورت جداگانه (مثل t.py)
            resp = ExternalAPIService.send_request(key, value)
            if resp is not None:
                results["sent"].append(
                    {"currency": key, "rate": value, "response": resp}
                )
                logger.info(f"{_LOG_PREFIX} send_rates_payload: POST success {key}={value}")
            else:
                results["failed"].append({"currency": key, "rate": value})
                logger.error(
                    f"{_LOG_PREFIX} send_rates_payload: FAILED to send {key} = {value}"
                )

        logger.info(
            f"{_LOG_PREFIX} send_rates_payload: summary sent={len(results['sent'])} "
            f"failed={len(results['failed'])}"
        )

        return results

    @staticmethod
    def _build_rates_from_items(items):
        """
        Build a dict of rates with STRICT filtering for external API.

        Only these 4 keys are ever produced:
        - USDT_BUY, USDT_SELL: ALL USDT price types (source/target USDT with IRR/IRT)
        - GBP_BUY, GBP_SELL: ONLY if PriceType.name contains 'حسابی' or 'account'

        Buy/Sell mapping: trade_type 'buy' -> *_BUY, 'sell' -> *_SELL.
        Duplicate keys: latest value wins.
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
                # Handle DecimalField properly - convert to float
                price_attr = getattr(price_history, "price", None)
                if price_attr is None:
                    price_value = 0.0
                else:
                    # Convert Decimal to float explicitly
                    price_value = float(price_attr)
                
                if source_code == "USDT" or target_code == "USDT":
                    logger.info(
                        f"{_LOG_PREFIX} _build_rates_from_items USDT: "
                        f"source={source_code} target={target_code} trade={trade_type} "
                        f"price={price_value} name={getattr(price_type, 'name', 'N/A')!r}"
                    )
            except Exception as exc:  # defensive
                logger.warning(f"Failed to extract price data from item {item}: {exc}")
                skipped.append(str(item))
                continue

            key = None

            # Main mapping: GBP / IRR and USDT / IRR
            pair = {source_code, target_code}
            price_type_name = (getattr(price_type, "name", "") or "").lower()

            if pair == {"GBP", "IRR"} or pair == {"GBP", "IRT"}:
                # برای پوند: فقط از "حسابی" (account) استفاده می‌کنیم، نه "نقدی" (cash)
                raw_name = getattr(price_type, "name", "")
                is_account = (
                    "حسابی" in raw_name
                    or "account" in price_type_name
                )
                logger.info(
                    f"{_LOG_PREFIX} _build_rates_from_items GBP: raw_name={raw_name!r} "
                    f"price_type_name={price_type_name!r} is_account={is_account}"
                )

                if is_account:
                    key = "GBP_BUY" if trade_type == "buy" else "GBP_SELL"
                    logger.info(
                        f"{_LOG_PREFIX} _build_rates_from_items: GBP account ACCEPTED "
                        f"{key}={price_value} price_type_name={raw_name!r}"
                    )
                else:
                    skip_reason = (
                        "GBP cash price skipped (only account/حسابی prices sent): "
                        f"{source_code}/{target_code} {trade_type} - {raw_name!r}"
                    )
                    skipped.append(skip_reason)
                    logger.info(
                        f"{_LOG_PREFIX} _build_rates_from_items: {skip_reason}"
                    )
                    continue
            elif pair == {"USDT", "IRR"} or pair == {"USDT", "IRT"}:
                # برای تتر: فقط به تومان (IRR) - همه قیمت‌های تتر به تومان ارسال می‌شوند
                # چه USDT/IRR باشد چه IRR/USDT، فقط نوع معامله برای BUY/SELL مهم است
                key = "USDT_BUY" if trade_type == "buy" else "USDT_SELL"

            if not key:
                skipped.append(f"{source_code}/{target_code} {trade_type}")
                continue

            if key in ("USDT_BUY", "USDT_SELL", "GBP_BUY", "GBP_SELL"):
                logger.info(
                    f"{_LOG_PREFIX} _build_rates_from_items: extracted {key}={price_value} "
                    f"source={source_code} target={target_code} trade={trade_type} "
                    f"name={getattr(price_type, 'name', 'N/A')!r}"
                )

            # Latest value wins if there are duplicates
            rates[key] = price_value

        # Strict: only allow the 4 API keys (safety in case of future logic changes)
        rates = {k: float(v) for k, v in rates.items() if k in RATE_KEYS}

        logger.info(
            f"{_LOG_PREFIX} _build_rates_from_items: result rates={rates} "
            f"skipped_count={len(skipped)} skipped={skipped}"
        )
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
        logger.info(
            f"{_LOG_PREFIX} send_finalized_prices: ENTRY item_count={len(price_items)}"
        )
        for idx, item in enumerate(price_items):
            if isinstance(item, tuple) and len(item) == 2:
                price_type, price_history = item
                source_code = (
                    getattr(getattr(price_type, "source_currency", None), "code", "N/A")
                    if hasattr(price_type, "source_currency")
                    else "N/A"
                )
                target_code = (
                    getattr(getattr(price_type, "target_currency", None), "code", "N/A")
                    if hasattr(price_type, "target_currency")
                    else "N/A"
                )
                trade_type = getattr(price_type, "trade_type", "N/A")
                price_value = getattr(price_history, "price", "N/A")
                name = getattr(price_type, "name", "N/A")
                logger.info(
                    f"{_LOG_PREFIX} send_finalized_prices: item[{idx}] "
                    f"source={source_code} target={target_code} trade={trade_type} "
                    f"price={price_value} name={name!r}"
                )

        rates, skipped = ExternalAPIService._build_rates_from_items(price_items)

        results = {
            "sent": [],
            "failed": [],
            "skipped": skipped,
        }

        if not rates:
            logger.warning(
                f"{_LOG_PREFIX} send_finalized_prices: NO rates extracted - "
                f"skipping API call. skipped={skipped}"
            )
            return results

        api_result = ExternalAPIService.send_rates_payload(rates)

        if api_result is not None:
            sent_count = len(api_result.get("sent", []))
            failed_count = len(api_result.get("failed", []))
            results["sent"].append(
                {"payload": rates, "response": api_result}
            )
            logger.info(
                f"{_LOG_PREFIX} send_finalized_prices: DONE rates_payload={rates} "
                f"api_result sent={sent_count} failed={failed_count}"
            )
        else:
            results["failed"].append({"payload": rates})
            logger.error(
                f"{_LOG_PREFIX} send_finalized_prices: send_rates_payload returned "
                f"None for rates={rates}"
            )

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
        logger.info(
            f"{_LOG_PREFIX} send_finalized_special_prices: ENTRY "
            f"item_count={len(special_price_items)}"
        )
        rates, skipped = ExternalAPIService._build_rates_from_items(
            special_price_items
        )

        results = {
            "sent": [],
            "failed": [],
            "skipped": skipped,
        }

        if not rates:
            logger.warning(
                f"{_LOG_PREFIX} send_finalized_special_prices: NO rates extracted - "
                f"skipping API call. skipped={skipped}"
            )
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

