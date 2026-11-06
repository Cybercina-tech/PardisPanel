"""Banner downloads: Standard plus Instagram Story / Post sizes, latest prices, nothing sent."""
import io
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import CustomUser
from category.models import Category, Currency, PriceType
from change_price.models import PriceHistory
from finalize.models import Finalization, SpecialPriceFinalization
from price_publisher.services.banner_formats import apply_format
from price_publisher.services.image_renderer import RenderedPriceImage
from special_price.models import SpecialPriceHistory, SpecialPricePair, SpecialPriceType


def _currency(code):
    obj, _ = Currency.objects.get_or_create(code=code, defaults={"name": code})
    return obj


def _png_bytes(size=(600, 400)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, "PNG")
    return buf.getvalue()


def _rendered():
    return RenderedPriceImage(stream=io.BytesIO(_png_bytes()), width=600, height=400)


def _size(content):
    return Image.open(io.BytesIO(content)).size


class ApplyFormatTest(TestCase):
    def test_sizes(self):
        src = _png_bytes()
        self.assertEqual(apply_format(src, "standard"), src)
        self.assertEqual(_size(apply_format(src, "story")), (1080, 1920))
        self.assertEqual(_size(apply_format(src, "post")), (1080, 1080))

    def test_tall_source_still_fits(self):
        self.assertEqual(_size(apply_format(_png_bytes((300, 1200)), "post")), (1080, 1080))

    def test_unknown_format(self):
        with self.assertRaises(ValueError):
            apply_format(_png_bytes(), "banner")


class BannerEndpointsTest(TestCase):
    def setUp(self):
        # The "finalize" throttle scope is counted in the shared cache; clear it so
        # these requests neither trip nor leak into other tests.
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = CustomUser.objects.create_user(
            username="mgr", password="x", role=CustomUser.ROLE_MANAGEMENT
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        gbp, irt, try_ = _currency("GBP"), _currency("IRT"), _currency("TRY")

        self.category = Category.objects.create(name="پوند", slug="pound")
        pt = PriceType.objects.create(
            category=self.category, name="buy", source_currency=gbp, target_currency=irt, trade_type="buy"
        )
        PriceHistory.objects.create(price_type=pt, price=Decimal("200000"))
        lira = PriceType.objects.create(
            category=self.category, name="lira", source_currency=try_, target_currency=irt, trade_type="buy"
        )
        PriceHistory.objects.create(price_type=lira, price=Decimal("1"))
        Category.objects.create(name="empty")

        self.spt = SpecialPriceType.objects.create(
            name="ویژه", source_currency=irt, target_currency=gbp, trade_type="buy"
        )
        pair = SpecialPricePair.objects.create(
            special_price_type=self.spt, name="p", source_currency=irt, target_currency=gbp, trade_type="buy"
        )
        self.hist = SpecialPriceHistory.objects.create(
            special_price_type=self.spt, pair=pair, price=Decimal("170000")
        )

    def _get_category(self, fmt=None):
        url = f"/api/finalize/category/{self.category.id}/banner/"
        with patch(
            "price_publisher.services.publisher.PricePublisherService._render_category_image",
            return_value=(_rendered(), None, "category_template_editor", None),
        ), patch("price_publisher.services.publisher.TelegramService") as telegram:
            response = self.client.get(url, {"size": fmt} if fmt else {})
        telegram.assert_not_called()
        return response

    def _get_special(self, fmt=None):
        with patch(
            "price_publisher.services.publisher.PricePublisherService._select_next_template_editor_for_special",
            return_value=(None, None),
        ), patch(
            "price_publisher.services.publisher.PricePublisherService._render_special_price_image",
            return_value=_rendered(),
        ), patch("price_publisher.services.publisher.TelegramService") as telegram:
            response = self.client.get(
                f"/api/finalize/special-price/{self.hist.id}/banner/", {"size": fmt} if fmt else {}
            )
        telegram.assert_not_called()
        return response

    def test_category_formats(self):
        for fmt, size in (("standard", (600, 400)), ("story", (1080, 1920)), ("post", (1080, 1080))):
            response = self._get_category(fmt)
            self.assertEqual(response.status_code, 200, getattr(response, "content", b"")[:200])
            self.assertEqual(_size(response.content), size)
        self.assertEqual(_size(self._get_category().content), (600, 400))  # default is standard
        self.assertIn("-story.png", self._get_category("story")["Content-Disposition"])
        self.assertFalse(Finalization.objects.exists())

    def test_special_formats(self):
        self.assertEqual(_size(self._get_special("story").content), (1080, 1920))
        self.assertEqual(_size(self._get_special("post").content), (1080, 1080))
        self.assertEqual(_size(self._get_special().content), (600, 400))
        self.assertFalse(SpecialPriceFinalization.objects.exists())

    def test_bad_format_is_400(self):
        self.assertEqual(self._get_category("gif").status_code, 400)
        self.assertEqual(self._get_special("gif").status_code, 400)

    def test_category_without_prices_is_400(self):
        empty = Category.objects.get(name="empty")
        response = self.client.get(f"/api/finalize/category/{empty.id}/banner/")
        self.assertEqual(response.status_code, 400)

    def test_requires_permission(self):
        anon = APIClient()
        self.assertIn(anon.get(f"/api/finalize/category/{self.category.id}/banner/").status_code, (401, 403))
        self.assertIn(anon.get("/api/finalize/banners/").status_code, (401, 403))

    def test_list_has_names_only_and_skips_empty(self):
        response = self.client.get("/api/finalize/banners/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["formats"], ["standard", "story", "post"])
        self.assertEqual([c["name"] for c in data["categories"]], ["پوند"])
        self.assertEqual(data["special_prices"], [{"id": self.spt.id, "history_id": self.hist.id, "name": "ویژه"}])
