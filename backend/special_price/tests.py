from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from category.models import Currency
from special_price.models import SpecialPriceHistory, SpecialPricePair, SpecialPriceType


class SpecialPriceMultiCurrencyTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="tester",
            password="secret123",
        )
        self.client.force_authenticate(self.user)

        self.irt, _ = Currency.objects.get_or_create(
            code="IRT", defaults={"name": "Toman", "symbol": "T"}
        )
        self.usdt, _ = Currency.objects.get_or_create(
            code="USDT", defaults={"name": "Tether", "symbol": "U"}
        )
        self.eur, _ = Currency.objects.get_or_create(
            code="EUR", defaults={"name": "Euro", "symbol": "E"}
        )

    def test_create_special_price_with_multiple_pairs(self):
        payload = {
            "name": "VIP Multi Pair",
            "source_currency_id": self.usdt.id,
            "target_currency_id": self.irt.id,
            "trade_type": "buy",
            "description": "test",
            "pair_inputs": [
                {
                    "name": "خرید ویژه تتر",
                    "source_currency_id": self.usdt.id,
                    "target_currency_id": self.irt.id,
                    "trade_type": "buy",
                },
                {
                    "name": "فروش ویژه تتر مخصوص برنامه نویس ها",
                    "source_currency_id": self.eur.id,
                    "target_currency_id": self.irt.id,
                    "trade_type": "sell",
                },
            ],
        }

        response = self.client.post("/api/special-prices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        sp = SpecialPriceType.objects.get(name="VIP Multi Pair")
        pairs = SpecialPricePair.objects.filter(special_price_type=sp)
        self.assertEqual(pairs.count(), 2)

    def test_multiple_pairs_must_not_all_have_same_trade_type(self):
        payload = {
            "name": "VIP Invalid Trades",
            "source_currency_id": self.usdt.id,
            "target_currency_id": self.irt.id,
            "trade_type": "buy",
            "pair_inputs": [
                {
                    "name": "buy 1",
                    "source_currency_id": self.usdt.id,
                    "target_currency_id": self.irt.id,
                    "trade_type": "buy",
                },
                {
                    "name": "buy 2",
                    "source_currency_id": self.eur.id,
                    "target_currency_id": self.irt.id,
                    "trade_type": "buy",
                },
            ],
        }
        response = self.client.post("/api/special-prices/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("errors", response.data)
        self.assertIn("pair_inputs", response.data["errors"])

    def test_update_price_for_selected_pair(self):
        # Price writes are management-only (mirrors the regular Price Hub RBAC).
        from accounts.models import CustomUser

        manager = CustomUser.objects.create_user(
            username="vip_manager",
            password="secret123",
            role=CustomUser.ROLE_MANAGEMENT,
        )
        self.client.force_authenticate(manager)

        sp = SpecialPriceType.objects.create(
            name="VIP Update",
            source_currency=self.usdt,
            target_currency=self.irt,
            trade_type="sell",
        )
        pair = SpecialPricePair.objects.create(
            special_price_type=sp,
            source_currency=self.eur,
            target_currency=self.irt,
        )

        response = self.client.post(
            reverse("api-special-price-update", kwargs={"pk": sp.id}),
            {"pair_id": pair.id, "price": "12345.00", "notes": "manual"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        history = SpecialPriceHistory.objects.get(id=response.data["id"])
        self.assertEqual(history.pair_id, pair.id)
        self.assertEqual(history.special_price_type_id, sp.id)
from django.test import TestCase

# Create your tests here.
