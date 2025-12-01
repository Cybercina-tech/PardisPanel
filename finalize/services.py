"""
Service for sending finalized prices to external API.
Based on the data.py reference file.
"""
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# API Configuration (from data.py reference)
EXTERNAL_API_URL = "https://sarafipardis.co.uk/wp-json/pardis/v1/rates"
EXTERNAL_API_KEY = "PX9k7mN2qR8vL4jH6wE3tY1uI5oP0aS9dF7gK2mN8xZ4cV6bQ1wE3rT5yU8iO0pL"


class ExternalAPIService:
    """
    Service to send price updates to external API.
    Handles GBP and USDT prices (buy/sell) similar to data.py functions.
    """
    
    @staticmethod
    def send_request(currency, rate):
        """
        Send a price update request to external API.
        
        Args:
            currency (str): Currency code (e.g., "GBP_BUY", "GBP_SELL", "USDT_BUY", "USDT_SELL")
            rate (float|Decimal|str): The price rate to send
        
        Returns:
            dict|None: Response JSON if successful, None on error
        """
        payload = {
            "currency": currency,
            "rate": float(rate),
            "api_key": EXTERNAL_API_KEY
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                EXTERNAL_API_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Successfully sent {currency} rate: {rate}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending {currency} rate {rate}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error sending {currency}: {e}")
            return None
    
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
            dict: Summary of sent prices with success/failure status
        """
        results = {
            "sent": [],
            "failed": [],
            "skipped": []
        }
        
        for item in price_items:
            # Handle both PriceType and SpecialPriceType
            if hasattr(item, 'price_type'):
                # Regular PriceType
                price_type = item.price_type
                price_history = item.price_history
            elif isinstance(item, tuple) and len(item) == 2:
                # Tuple format: (price_type, price_history)
                price_type, price_history = item
            else:
                logger.warning(f"Unknown price item format: {item}")
                results["skipped"].append(str(item))
                continue
            
            # Get currency codes
            source_code = price_type.source_currency.code.upper()
            target_code = price_type.target_currency.code.upper()
            trade_type = price_type.trade_type  # 'buy' or 'sell'
            price_value = float(price_history.price)
            
            # Only process GBP and USDT prices
            currency_to_send = None
            
            if source_code == "GBP" and target_code == "IRR":
                currency_to_send = f"GBP_{trade_type.upper()}"
            elif source_code == "USDT" and target_code == "IRR":
                currency_to_send = f"USDT_{trade_type.upper()}"
            else:
                # Not GBP or USDT, skip
                results["skipped"].append(f"{source_code}/{target_code} {trade_type}")
                continue
            
            # Send to API
            api_result = ExternalAPIService.send_request(currency_to_send, price_value)
            
            if api_result is not None:
                results["sent"].append({
                    "currency": currency_to_send,
                    "rate": price_value,
                    "response": api_result
                })
            else:
                results["failed"].append({
                    "currency": currency_to_send,
                    "rate": price_value
                })
        
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
        results = {
            "sent": [],
            "failed": [],
            "skipped": []
        }
        
        for item in special_price_items:
            if isinstance(item, tuple) and len(item) == 2:
                special_price_type, special_price_history = item
            else:
                logger.warning(f"Unknown special price item format: {item}")
                results["skipped"].append(str(item))
                continue
            
            # Get currency codes
            source_code = special_price_type.source_currency.code.upper()
            target_code = special_price_type.target_currency.code.upper()
            trade_type = special_price_type.trade_type  # 'buy' or 'sell'
            price_value = float(special_price_history.price)
            
            # Only process GBP and USDT prices
            currency_to_send = None
            
            if source_code == "GBP" and target_code == "IRR":
                currency_to_send = f"GBP_{trade_type.upper()}"
            elif source_code == "USDT" and target_code == "IRR":
                currency_to_send = f"USDT_{trade_type.upper()}"
            else:
                # Not GBP or USDT, skip
                results["skipped"].append(f"{source_code}/{target_code} {trade_type}")
                continue
            
            # Send to API
            api_result = ExternalAPIService.send_request(currency_to_send, price_value)
            
            if api_result is not None:
                results["sent"].append({
                    "currency": currency_to_send,
                    "rate": price_value,
                    "response": api_result
                })
            else:
                results["failed"].append({
                    "currency": currency_to_send,
                    "rate": price_value
                })
        
        return results

