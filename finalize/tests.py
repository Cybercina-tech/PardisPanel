from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal

from category.models import Category, Currency, PriceType
from change_price.models import PriceHistory
from finalize.services import ExternalAPIService


class ExternalAPIServiceTest(TestCase):
    """Test cases for ExternalAPIService"""

    def setUp(self):
        """Set up test data"""
        # Create currencies
        self.usdt_currency = Currency.objects.create(
            code='USDT',
            name='Tether',
            symbol='USDT'
        )
        self.irr_currency = Currency.objects.create(
            code='IRR',
            name='Iranian Rial',
            symbol='IRR'
        )
        self.gbp_currency = Currency.objects.create(
            code='GBP',
            name='British Pound',
            symbol='GBP'
        )

        # Create category
        self.tether_category = Category.objects.create(
            name='تتر',
            description='Tether category'
        )

        # Create price types
        self.usdt_sell_price_type = PriceType.objects.create(
            category=self.tether_category,
            name='فروش تتر تومان',
            source_currency=self.usdt_currency,
            target_currency=self.irr_currency,
            trade_type='sell'
        )

        self.usdt_buy_price_type = PriceType.objects.create(
            category=self.tether_category,
            name='خرید تتر تومان',
            source_currency=self.usdt_currency,
            target_currency=self.irr_currency,
            trade_type='buy'
        )

    @patch('finalize.services.requests.post')
    @patch('finalize.services.requests.get')
    def test_send_usdt_sell_price_150000(self, mock_get, mock_post):
        """Test sending USDT sell price of 150000 toman"""
        # Mock the GET request for existing rates (return empty dict)
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {}
        mock_get_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_response

        # Mock the POST requests for sending rates
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"status": "success"}
        mock_post_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_post_response

        # Create price history with 150000 toman
        price_history = PriceHistory.objects.create(
            price_type=self.usdt_sell_price_type,
            price=Decimal('150000.00')
        )

        # Prepare price items
        price_items = [
            (self.usdt_sell_price_type, price_history)
        ]

        # Send finalized prices
        results = ExternalAPIService.send_finalized_prices(price_items)

        # Verify results
        self.assertIn("sent", results)
        self.assertIn("failed", results)
        self.assertIn("skipped", results)

        # Check that POST was called for USDT_SELL
        post_calls = mock_post.call_args_list
        usdt_sell_called = False
        usdt_sell_rate = None

        for call in post_calls:
            args, kwargs = call
            payload = kwargs.get('json', {})
            if payload.get('currency') == 'USDT_SELL':
                usdt_sell_called = True
                usdt_sell_rate = payload.get('rate')
                break

        # Assertions
        self.assertTrue(usdt_sell_called, "USDT_SELL should be sent to API")
        self.assertEqual(
            usdt_sell_rate, 
            150000.0, 
            f"USDT_SELL rate should be 150000.0, but got {usdt_sell_rate}"
        )

        # Verify the rate was sent correctly
        self.assertIn("sent", results)
        if results["sent"]:
            sent_payload = results["sent"][0].get("payload", {})
            self.assertIn("USDT_SELL", sent_payload)
            self.assertEqual(sent_payload["USDT_SELL"], 150000.0)

    @patch('finalize.services.requests.post')
    @patch('finalize.services.requests.get')
    def test_send_usdt_buy_and_sell_prices(self, mock_get, mock_post):
        """Test sending both USDT buy and sell prices"""
        # Mock the GET request for existing rates
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {}
        mock_get_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_response

        # Mock the POST requests
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"status": "success"}
        mock_post_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_post_response

        # Create price histories
        buy_price_history = PriceHistory.objects.create(
            price_type=self.usdt_buy_price_type,
            price=Decimal('148000.00')
        )

        sell_price_history = PriceHistory.objects.create(
            price_type=self.usdt_sell_price_type,
            price=Decimal('150000.00')
        )

        # Prepare price items
        price_items = [
            (self.usdt_buy_price_type, buy_price_history),
            (self.usdt_sell_price_type, sell_price_history)
        ]

        # Send finalized prices
        results = ExternalAPIService.send_finalized_prices(price_items)

        # Check POST calls
        post_calls = mock_post.call_args_list
        rates_sent = {}

        for call in post_calls:
            args, kwargs = call
            payload = kwargs.get('json', {})
            currency = payload.get('currency')
            rate = payload.get('rate')
            if currency:
                rates_sent[currency] = rate

        # Verify both rates were sent
        self.assertIn("USDT_BUY", rates_sent)
        self.assertIn("USDT_SELL", rates_sent)
        self.assertEqual(rates_sent["USDT_BUY"], 148000.0)
        self.assertEqual(rates_sent["USDT_SELL"], 150000.0)

    @patch('finalize.services.requests.post')
    @patch('finalize.services.requests.get')
    def test_usdt_sell_price_not_overwritten_by_existing_api_value(self, mock_get, mock_post):
        """Test that USDT_SELL price is not overwritten by existing API value of 1"""
        # Mock the GET request to return existing rate with invalid value (1)
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = {
            "USDT_SELL": 1.0,  # Invalid existing value
            "USDT_BUY": 148000.0,
            "GBP_BUY": 65000.0,
            "GBP_SELL": 67000.0
        }
        mock_get_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_get_response

        # Mock the POST requests
        mock_post_response = MagicMock()
        mock_post_response.json.return_value = {"status": "success"}
        mock_post_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_post_response

        # Create price history with valid price
        sell_price_history = PriceHistory.objects.create(
            price_type=self.usdt_sell_price_type,
            price=Decimal('150000.00')
        )

        # Prepare price items
        price_items = [
            (self.usdt_sell_price_type, sell_price_history)
        ]

        # Send finalized prices
        results = ExternalAPIService.send_finalized_prices(price_items)

        # Check that USDT_SELL was sent with the correct value (150000), not 1
        post_calls = mock_post.call_args_list
        usdt_sell_rate = None

        for call in post_calls:
            args, kwargs = call
            payload = kwargs.get('json', {})
            if payload.get('currency') == 'USDT_SELL':
                usdt_sell_rate = payload.get('rate')
                break

        # Verify the correct rate was sent
        self.assertIsNotNone(usdt_sell_rate, "USDT_SELL should be sent")
        self.assertEqual(
            usdt_sell_rate, 
            150000.0, 
            f"USDT_SELL rate should be 150000.0, not {usdt_sell_rate}"
        )
        self.assertNotEqual(
            usdt_sell_rate, 
            1.0, 
            "USDT_SELL rate should not be 1.0 (invalid existing value)"
        )
