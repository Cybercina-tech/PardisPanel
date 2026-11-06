"""Guarantees carried over from the Pardis panel.

* ``GET /prices/live-json/`` is a public contract with third-party sites.
* Lira (TRY) never enters a finalize flow.
* A special-price banner can be downloaded without publishing anything.
"""
import io
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from accounts.models import CustomUser
from category.models import Category, Currency, PriceType
from change_price.models import PriceHistory
from finalize.api_views import FinalizeCategoryAPIView
from finalize.services import _build_rates_from_items
from price_publisher.services.image_renderer import RenderedPriceImage
from special_price.models import SpecialPriceHistory, SpecialPricePair, SpecialPriceType
from telegram_app.models import TelegramBot, TelegramChannel


def _currency(code):
    obj, _ = Currency.objects.get_or_create(code=code, defaults={"name": code})
    return obj


class LivePricesJsonContractTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="تتر")
        gbp, irt = _currency("GBP"), _currency("IRT")
        # Created out of name order on purpose: Pardis listed price types by name.
        self.b = PriceType.objects.create(
            category=self.cat, name="b-sell", source_currency=gbp, target_currency=irt, trade_type="sell"
        )
        self.a = PriceType.objects.create(
            category=self.cat, name="a-buy", source_currency=gbp, target_currency=irt, trade_type="buy"
        )
        PriceHistory.objects.create(price_type=self.a, price=Decimal("163000"))

    def test_public_shape_order_and_formats(self):
        response = self.client.get("/prices/live-json/")  # anonymous
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"count", "prices"})
        self.assertEqual(body["count"], 2)
        first, second = body["prices"]
        self.assertEqual(
            set(first),
            {
                "category_name", "price_type_name", "trade_type",
                "source_currency", "target_currency", "latest_price", "updated_at",
            },
        )
        self.assertEqual(first["price_type_name"], self.a.slug)  # "a-buy" sorts first
        self.assertEqual(first["latest_price"], "163000.00")  # string, 2 decimals
        self.assertIsNone(second["latest_price"])
        self.assertIsNone(second["updated_at"])

    def test_only_get_is_allowed(self):
        self.assertEqual(self.client.post("/prices/live-json/").status_code, 405)


class LiraExcludedFromFinalizeTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgr", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        self.cat = Category.objects.create(name="تتر")
        usdt, irt, try_ = _currency("USDT"), _currency("IRT"), _currency("TRY")
        self.usdt_type = PriceType.objects.create(
            category=self.cat, name="خرید تتر", source_currency=usdt, target_currency=irt, trade_type="buy"
        )
        self.lira_type = PriceType.objects.create(
            category=self.cat, name="لیر", source_currency=try_, target_currency=irt, trade_type="buy"
        )
        self.usdt_hist = PriceHistory.objects.create(price_type=self.usdt_type, price=Decimal("126000"))
        self.lira_hist = PriceHistory.objects.create(price_type=self.lira_type, price=Decimal("3100"))
        bot = TelegramBot.objects.create(name="bot", token="t")
        self.channel = TelegramChannel.objects.create(bot=bot, name="main", chat_id="@c")

    def test_dashboard_has_no_lira_rows(self):
        client = APIClient()
        client.force_authenticate(self.user)
        data = client.get("/api/finalize/dashboard/").json()
        names = [
            p["price_type_name"]
            for c in data["pending_by_category"]
            for p in c["pending_prices"]
        ]
        self.assertEqual(names, ["خرید تتر"])

    @patch("finalize.api_views.ExternalAPIService.send_finalized_prices")
    @patch("finalize.api_views.publish_category_prices_task.apply_async")
    def test_finalize_publishes_and_pushes_without_lira(self, mock_publish, mock_push):
        mock_push.return_value = {"sent": [], "failed": [], "skipped": []}
        result = MagicMock()
        result.get.return_value = {"success": True, "response": "ok", "caption": "c"}
        mock_publish.return_value = result

        request = APIRequestFactory().post(
            f"/api/finalize/category/{self.cat.id}/",
            {"channel_id": self.channel.id, "notes": ""},
            format="json",
        )
        force_authenticate(request, user=self.user)
        FinalizeCategoryAPIView.as_view()(request, category_id=self.cat.id)

        sent_ids = mock_publish.call_args.kwargs["kwargs"]["price_history_ids"]
        self.assertEqual(sent_ids, [self.usdt_hist.id])
        pushed = [pt.id for pt, _ in mock_push.call_args.args[0]]
        self.assertEqual(pushed, [self.usdt_type.id])

    def test_external_rates_never_contain_lira(self):
        items = [(self.usdt_type, self.usdt_hist), (self.lira_type, self.lira_hist)]
        rates, _ = _build_rates_from_items(items)
        self.assertEqual(rates, {"USDT_BUY": 126000.0})


class SpecialBannerDownloadTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgr", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        gbp, irt = _currency("GBP"), _currency("IRT")
        self.spt = SpecialPriceType.objects.create(
            name="قیمت ویژه", source_currency=irt, target_currency=gbp, trade_type="buy"
        )
        pair = SpecialPricePair.objects.create(
            special_price_type=self.spt, name="p", source_currency=irt, target_currency=gbp, trade_type="buy"
        )
        self.hist = SpecialPriceHistory.objects.create(
            special_price_type=self.spt, pair=pair, price=Decimal("170000")
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _png(self):
        buf = io.BytesIO()
        Image.new("RGB", (4, 4), "white").save(buf, "PNG")
        buf.seek(0)
        return RenderedPriceImage(stream=buf, width=4, height=4)

    @patch("price_publisher.services.publisher.TelegramService")
    @patch(
        "price_publisher.services.publisher.PricePublisherService._select_next_template_editor_for_special",
        return_value=(None, None),
    )
    @patch("price_publisher.services.publisher.PricePublisherService._render_special_price_image")
    def test_download_returns_png_and_sends_nothing(self, mock_render, _sel, mock_telegram):
        mock_render.return_value = self._png()
        response = self.client.get(f"/api/finalize/special-price/{self.hist.id}/banner/")
        self.assertEqual(response.status_code, 200, getattr(response, "content", b"")[:200])
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"\x89PNG"))
        mock_telegram.assert_not_called()  # nothing uploaded to any channel
        from finalize.models import SpecialPriceFinalization

        self.assertFalse(SpecialPriceFinalization.objects.exists())  # not finalized either

    def test_requires_authentication(self):
        response = APIClient().get(f"/api/finalize/special-price/{self.hist.id}/banner/")
        self.assertIn(response.status_code, (401, 403))


class TelegramContentCarriedOverTest(TestCase):
    """A banner is never published bare: Pardis caption and buttons always go with it."""

    def setUp(self):
        from price_publisher.services.publisher import PricePublisherService

        self.service = PricePublisherService()

    def test_category_without_configured_content_gets_pardis_caption_and_buttons(self):
        for name, marker in (("تتر", "تاریخ"), ("پوند", "GBP"), ("درهم", "آدرس دفتر")):
            cat = Category.objects.create(name=name)
            caption = self.service._build_category_publish_caption(cat, [], None, None)
            self.assertIn(marker, caption, name)
            buttons = self.service._build_category_publish_buttons(cat, None)
            self.assertEqual(len(buttons), 4)
            self.assertEqual(buttons[3][0]["url"], "https://sarafipardis.co.uk/")
            self.assertEqual(buttons[3][1]["url"], "https://www.instagram.com/sarafipardis")

    def test_configured_category_buttons_win_over_default(self):
        cat = Category.objects.create(name="درهم", inline_buttons=[{"label": "Hi", "url": "https://x.test"}])
        self.assertEqual(
            self.service._build_category_publish_buttons(cat, None),
            [[{"text": "Hi", "url": "https://x.test"}]],
        )

    def test_double_price_special_has_no_caption(self):
        spt = SpecialPriceType.objects.create(
            name="x", source_currency=_currency("GBP"), target_currency=_currency("IRT"),
            trade_type="buy", is_double_price=True,
        )
        self.assertEqual(self.service._build_special_price_caption(spt, None, True), "")


class FinalizeLeavesNothingPendingTest(TestCase):
    """After finalizing everything, the dashboard must list nothing."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgr2", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        self.cat = Category.objects.create(name="پوند")
        gbp, irt = _currency("GBP"), _currency("IRT")
        self.a = PriceType.objects.create(
            category=self.cat, name="a", source_currency=gbp, target_currency=irt, trade_type="buy"
        )
        self.b = PriceType.objects.create(
            category=self.cat, name="b", source_currency=gbp, target_currency=irt, trade_type="sell"
        )
        PriceHistory.objects.create(price_type=self.a, price=Decimal("1"))
        PriceHistory.objects.create(price_type=self.b, price=Decimal("2"))
        bot = TelegramBot.objects.create(name="bot2", token="t")
        self.channel = TelegramChannel.objects.create(bot=bot, name="main2", chat_id="@c2")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _finalize(self):
        with patch("finalize.api_views.ExternalAPIService.send_finalized_prices") as push, patch(
            "finalize.api_views.publish_category_prices_task.apply_async"
        ) as publish:
            push.return_value = {"sent": [], "failed": [], "skipped": []}
            publish.return_value.get.return_value = {"success": True, "response": "ok", "caption": "c"}
            response = self.client.post(
                f"/api/finalize/category/{self.cat.id}/",
                {"channel_id": self.channel.id, "notes": ""},
                format="json",
            )
        self.assertEqual(response.status_code, 201, response.content)
        return publish.call_args.kwargs["kwargs"]["price_history_ids"]

    def _pending(self):
        return [
            p["price_type_name"]
            for c in self.client.get("/api/finalize/dashboard/").json()["pending_by_category"]
            for p in c["pending_prices"]
        ]

    def test_partial_update_then_finalize_leaves_nothing_pending(self):
        self._finalize()
        self.assertEqual(self._pending(), [])
        PriceHistory.objects.create(price_type=self.a, price=Decimal("11"))  # only `a` changes
        self.assertEqual(self._pending(), ["a"])
        sent = self._finalize()
        self.assertEqual(len(sent), 2)  # banner still shows both rows
        self.assertEqual(self._pending(), [])  # `b` must not resurface


class PardisTelegramContentSeedTest(TestCase):
    def setUp(self):
        from accounts.models import Account

        self.account = Account.objects.create(name="P", slug="pardis-t")

    def test_seed_fills_only_empty_fields_and_keeps_button_rows(self):
        from accounts.management.commands.apply_pardis_branding import apply_telegram_content
        from accounts.scoping import act_as_account
        from price_publisher.services.publisher import PricePublisherService, _normalize_inline_keyboard

        with act_as_account(self.account.pk):
            tether = Category.objects.create(name="سایر ارز ها")
            edited = Category.objects.create(name="پوند", telegram_message_description="mine")
            self.assertEqual(apply_telegram_content(self.account), 2)
            tether.refresh_from_db()
            edited.refresh_from_db()
            self.assertIn("{date_fa}", tether.telegram_message_description)
            self.assertEqual(edited.telegram_message_description, "mine")  # edit kept
            rows = _normalize_inline_keyboard(tether.inline_buttons)
            self.assertEqual([len(r) for r in rows], [1, 1, 1, 2])  # website + Instagram side by side
            self.assertEqual(apply_telegram_content(self.account), 0)  # idempotent
            caption = PricePublisherService()._build_category_publish_caption(tether, [], None, None)
            self.assertNotIn("{date_fa}", caption)  # variables are filled at publish time


class DoublePriceSpecialTest(TestCase):
    """Cash and account prices are entered together and reach the finalize dashboard."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgr3", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        gbp, irt = _currency("GBP"), _currency("IRT")
        self.spt = SpecialPriceType.objects.create(
            name="نقدی و حسابی", source_currency=irt, target_currency=gbp,
            trade_type="buy", is_double_price=True,
        )
        self.pair = SpecialPricePair.objects.create(
            special_price_type=self.spt, name="p", source_currency=irt, target_currency=gbp, trade_type="buy"
        )
        bot = TelegramBot.objects.create(name="bot3", token="t")
        TelegramChannel.objects.create(bot=bot, name="main3", chat_id="@c3")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_update_requires_both_prices_then_dashboard_shows_both(self):
        url = f"/api/special-prices/{self.spt.id}/update-price/"
        r = self.client.post(url, {"pair_id": self.pair.id, "cash_price": "170000"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post(
            url, {"pair_id": self.pair.id, "cash_price": "170000", "account_price": "175000"}, format="json"
        )
        self.assertIn(r.status_code, (200, 201), r.content)
        pending = self.client.get("/api/finalize/dashboard/").json()["pending_special_prices"]
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0]["is_double_price"])
        self.assertEqual(pending[0]["cash_price"], "170000.00")
        self.assertEqual(pending[0]["account_price"], "175000.00")


class BulkUpdateRetainsPreviousPricesTest(TestCase):
    """A price type with no slug (the Euro row) saves, and its last price comes back for prefill."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username="mgr4", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        eur, irt = _currency("EUR"), _currency("IRT")
        self.cat = Category.objects.create(name="سایر ارز ها")
        self.euro = PriceType.objects.create(
            category=self.cat, name="یورو", source_currency=eur, target_currency=irt, trade_type="buy"
        )
        PriceType.objects.filter(pk=self.euro.pk).update(slug="")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_euro_saved_and_returned_as_latest(self):
        url = f"/api/prices/category/{self.cat.id}/bulk-update/"
        r = self.client.post(url, {"prices": {str(self.euro.id): "190000"}}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(PriceHistory.objects.filter(price_type=self.euro).count(), 1)
        rows = self.client.get("/api/prices/").json()
        euro = next(p for p in rows if p["id"] == self.euro.id)
        self.assertEqual(euro["latest_price"], "190000.00")
