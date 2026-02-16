from django.test import TestCase, override_settings
from unittest.mock import patch, MagicMock
from decimal import Decimal

from category.models import Category, Currency, PriceType
from change_price.models import PriceHistory
from finalize.services import ExternalAPIService


@override_settings(
    EXTERNAL_API_URL='https://test.example/rates',
    EXTERNAL_API_KEY='test-api-key'
)
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
    def test_send_usdt_sell_price_150000(self, mock_post):
        """Test sending USDT sell price of 150000 toman"""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post.return_value = mock_post_response

        price_history = PriceHistory.objects.create(
            price_type=self.usdt_sell_price_type,
            price=Decimal('150000.00')
        )
        price_items = [(self.usdt_sell_price_type, price_history)]

        results = ExternalAPIService.send_finalized_prices(price_items)

        self.assertIn("sent", results)
        self.assertIn("failed", results)
        self.assertIn("skipped", results)

        post_calls = mock_post.call_args_list
        usdt_sell_called = False
        usdt_sell_rate = None
        for call in post_calls:
            payload = call[1].get('json', {})
            if payload.get('currency') == 'USDT_SELL':
                usdt_sell_called = True
                usdt_sell_rate = payload.get('rate')
                break

        self.assertTrue(usdt_sell_called, "USDT_SELL should be sent to API")
        self.assertEqual(usdt_sell_rate, 150000.0)

        self.assertEqual(len(results["sent"]), 1)
        self.assertEqual(results["sent"][0]["currency"], "USDT_SELL")
        self.assertEqual(results["sent"][0]["rate"], 150000.0)

    @patch('finalize.services.requests.post')
    def test_send_usdt_buy_and_sell_prices(self, mock_post):
        """Test sending both USDT buy and sell prices"""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
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
    def test_usdt_sell_price_not_overwritten_by_existing_api_value(self, mock_post):
        """Test that USDT_SELL is sent with value from price_items (no API fetch)"""
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
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

    @patch('finalize.services.requests.post')
    def test_usdt_gbp_pair_skipped(self, mock_post):
        """Test that USDT/GBP pairs are NOT sent (only USDT/IRR)"""
        usdt_gbp_type = PriceType.objects.create(
            category=self.tether_category,
            name='تتر به پوند',
            source_currency=self.usdt_currency,
            target_currency=self.gbp_currency,
            trade_type='sell'
        )
        price_history = PriceHistory.objects.create(
            price_type=usdt_gbp_type,
            price=Decimal('0.79')
        )
        price_items = [(usdt_gbp_type, price_history)]

        results = ExternalAPIService.send_finalized_prices(price_items)

        self.assertEqual(len(results["sent"]), 0, "USDT/GBP should not be sent")
        self.assertGreater(len(results["skipped"]), 0)
        self.assertEqual(mock_post.call_count, 0, "No POST for USDT/GBP")

    @patch('finalize.services.requests.post')
    def test_gbp_account_only_sent(self, mock_post):
        """Test that only GBP account (حسابی) is sent, not cash"""
        gbp_account_type = PriceType.objects.create(
            category=Category.objects.create(name='پوند', description='Pound'),
            name='خرید حسابی',
            source_currency=self.gbp_currency,
            target_currency=self.irr_currency,
            trade_type='buy'
        )
        gbp_cash_type = PriceType.objects.create(
            category=gbp_account_type.category,
            name='خرید نقدی',
            source_currency=self.gbp_currency,
            target_currency=self.irr_currency,
            trade_type='buy'
        )
        mock_post.return_value = MagicMock(status_code=200)

        price_items = [
            (gbp_account_type, PriceHistory.objects.create(price_type=gbp_account_type, price=Decimal('163000'))),
            (gbp_cash_type, PriceHistory.objects.create(price_type=gbp_cash_type, price=Decimal('162000')))
        ]

        results = ExternalAPIService.send_finalized_prices(price_items)

        self.assertEqual(len(results["sent"]), 1)
        self.assertEqual(results["sent"][0]["currency"], "GBP_BUY")
        self.assertEqual(results["sent"][0]["rate"], 163000.0)
        self.assertEqual(mock_post.call_count, 1, "Only GBP account sent")
