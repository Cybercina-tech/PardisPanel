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

        logger.info(f"🔄 Attempting to send {currency} = {rate} to {EXTERNAL_API_URL}")
        logger.info(f"   Payload: {payload}")

        try:
            response = requests.post(
                EXTERNAL_API_URL,
                json=payload,
                headers=headers,
                timeout=10,  # مطابق t.py
            )
            
            logger.info(f"   Response status: {response.status_code}")
            logger.info(f"   Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            # بعضی نسخه‌ها چیزی برنمی‌گردانند، پس json لازم نیست حتماً باشد
            try:
                result = response.json()
                logger.info(f"   Response JSON: {result}")
            except ValueError:
                result = {"raw": response.text}
                logger.info(f"   Response text: {response.text[:200]}")
            
            logger.info(f"✅ Successfully sent {currency} rate: {rate}")
            return result
            
        except requests.exceptions.Timeout as e:
            logger.error(f"❌ Timeout error sending {currency} rate {rate}: {e}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ Connection error sending {currency} rate {rate}: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ HTTP error sending {currency} rate {rate}: {e}")
            logger.error(f"   Response status: {e.response.status_code if e.response else 'N/A'}")
            logger.error(f"   Response text: {e.response.text[:500] if e.response else 'N/A'}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error sending {currency} rate {rate}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error sending {currency}: {e}", exc_info=True)
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
        ارسال هر 4 قیمت به صورت جداگانه - دقیقاً مطابق t.py:
        همیشه هر 4 کلید (GBP_BUY, GBP_SELL, USDT_BUY, USDT_SELL) را می‌فرستد.
        - اگر برای یک کلید قیمت جدید داریم: همان را می‌فرستیم
        - اگر نداریم، مقدار قبلی را از API می‌خوانیم
        - اگر هیچ مقداری وجود نداشته باشد، آن کلید را با مقدار 0 می‌فرستیم
        
        هر قیمت به صورت جداگانه با یک درخواست POST ارسال می‌شود (مثل t.py).
        """
        # Get previous values from external API
        existing = ExternalAPIService.get_existing_rates() or {}
        logger.info(f"Existing rates from API: {existing}")
        logger.info(f"New rates to send: {rates}")

        # همیشه هر 4 قیمت را آماده می‌کنیم
        full_rates: dict[str, float] = {}
        for key in RATE_KEYS:
            if key in rates:
                # Always use new rate if available (even if it's 0 or 1)
                rate_value = float(rates[key])
                full_rates[key] = rate_value
                logger.info(f"Using new rate for {key}: {full_rates[key]}")
            elif key in existing:
                # Use existing rate from API if no new rate available
                existing_value = float(existing[key])
                full_rates[key] = existing_value
                logger.info(f"Using existing rate from API for {key}: {full_rates[key]}")
            else:
                # No new or previous value → fall back to 0
                full_rates[key] = 0.0
                logger.warning(f"No rate found for {key}, using 0.0")

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

        # ارسال هر 4 قیمت به صورت جداگانه - دقیقاً مطابق t.py
        # برای هر قیمت یک درخواست POST جداگانه با payload:
        # {"currency": "GBP_BUY", "rate": 163000, "api_key": "..."}
        logger.info(f"📤 Starting to send {len(full_rates)} rates to API...")
        results = {"sent": [], "failed": []}
        
        for key, value in full_rates.items():
            logger.info(f"📨 Sending {key} = {value}...")
            # ارسال هر قیمت به صورت جداگانه (مثل t.py)
            resp = ExternalAPIService.send_request(key, value)
            if resp is not None:
                results["sent"].append(
                    {"currency": key, "rate": value, "response": resp}
                )
                logger.info(f"✅ Successfully sent {key} = {value}")
            else:
                results["failed"].append({"currency": key, "rate": value})
                logger.error(f"❌ Failed to send {key} = {value}")
        
        logger.info(f"📊 API send summary: {len(results['sent'])} sent, {len(results['failed'])} failed")

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
                # Handle DecimalField properly - convert to float
                price_attr = getattr(price_history, "price", None)
                if price_attr is None:
                    price_value = 0.0
                else:
                    # Convert Decimal to float explicitly
                    price_value = float(price_attr)
                
                # Log all USDT-related items for debugging
                if source_code == "USDT" or target_code == "USDT":
                    logger.info(
                        f"Processing USDT item: source={source_code}, target={target_code}, "
                        f"trade_type={trade_type}, price={price_value}, "
                        f"price_type_name={getattr(price_type, 'name', 'N/A')}"
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
                # بررسی می‌کنیم که آیا "حسابی" یا "account" در نام price_type وجود دارد
                is_account = "حسابی" in getattr(price_type, "name", "") or "account" in price_type_name
                
                if is_account:
                    # چه GBP/IRR باشد چه IRR/GBP، فقط نوع معامله برای BUY/SELL مهم است
                    key = "GBP_BUY" if trade_type == "buy" else "GBP_SELL"
                    logger.info(
                        f"GBP account price found: {key} = {price_value}, "
                        f"price_type_name={getattr(price_type, 'name', 'N/A')}"
                    )
                else:
                    # پوند نقدی را skip می‌کنیم
                    skipped.append(
                        f"GBP cash price skipped (only account prices are sent): "
                        f"{source_code}/{target_code} {trade_type} - {getattr(price_type, 'name', 'N/A')}"
                    )
                    continue
            elif pair == {"USDT", "IRR"} or pair == {"USDT", "IRT"}:
                # برای تتر: فقط به تومان (IRR) - همه قیمت‌های تتر به تومان ارسال می‌شوند
                # چه USDT/IRR باشد چه IRR/USDT، فقط نوع معامله برای BUY/SELL مهم است
                key = "USDT_BUY" if trade_type == "buy" else "USDT_SELL"

            if not key:
                skipped.append(f"{source_code}/{target_code} {trade_type}")
                continue

            # Log for debugging rates specifically
            if key in ("USDT_BUY", "USDT_SELL", "GBP_BUY", "GBP_SELL"):
                logger.info(
                    f"{key} price extracted: source={source_code}, target={target_code}, "
                    f"trade_type={trade_type}, price_value={price_value}, "
                    f"price_type_name={getattr(price_type, 'name', 'N/A')}, "
                    f"price_type_id={getattr(price_type, 'id', 'N/A')}"
                )

            # Latest value wins if there are duplicates
            rates[key] = price_value

        logger.info(f"Built rates dict: {rates}, skipped: {skipped}")
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
        # Log input items for debugging
        logger.info(f"send_finalized_prices called with {len(price_items)} items")
        for idx, item in enumerate(price_items):
            if isinstance(item, tuple) and len(item) == 2:
                price_type, price_history = item
                source_code = getattr(getattr(price_type, 'source_currency', None), 'code', 'N/A') if hasattr(price_type, 'source_currency') else 'N/A'
                target_code = getattr(getattr(price_type, 'target_currency', None), 'code', 'N/A') if hasattr(price_type, 'target_currency') else 'N/A'
                trade_type = getattr(price_type, 'trade_type', 'N/A')
                price_value = getattr(price_history, 'price', 'N/A')
                logger.info(
                    f"  Item {idx}: {source_code}/{target_code} {trade_type} = {price_value} "
                    f"(price_type: {getattr(price_type, 'name', 'N/A')})"
                )
        
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

