from django.test import SimpleTestCase

from price_publisher.services.pardis_captions import (
    GBP_CAPTION,
    PRICE_NOTICE,
    TETHER_CAPTION,
    with_price_notice,
)


class PriceNoticeTests(SimpleTestCase):
    def test_appended_after_caption(self):
        out = with_price_notice("hello")
        self.assertTrue(out.startswith("hello\n\n"))
        self.assertTrue(out.endswith(PRICE_NOTICE))

    def test_idempotent(self):
        once = with_price_notice("hello")
        self.assertEqual(with_price_notice(once), once)

    def test_empty_caption_is_just_the_notice(self):
        self.assertEqual(with_price_notice(None), PRICE_NOTICE)

    def test_fits_telegram_caption_limit(self):
        for caption in (TETHER_CAPTION, GBP_CAPTION):
            self.assertLess(len(with_price_notice(caption)), 1024)


from io import BytesIO, StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from category.models import Category
from price_publisher.services.image_renderer import RenderedPriceImage
from price_publisher.services.publisher import PricePublisherService


class SendPathNoticeTests(TestCase):
    def test_publisher_send_photo_appends_notice_to_the_wire_caption(self):
        channel = mock.Mock(chat_id="-100", bot=mock.Mock(get_plain_token=lambda: "t"))
        with mock.patch("price_publisher.services.publisher.TelegramService") as svc:
            svc.return_value.send_photo.return_value = (True, "ok")
            result = PricePublisherService(acting_user=None)._send_photo(
                channel=channel,
                image=RenderedPriceImage(stream=BytesIO(b"png"), width=1, height=1),
                caption="custom caption",
            )
        sent = svc.return_value.send_photo.call_args.kwargs["caption"]
        self.assertTrue(sent.startswith("custom caption\n\n"))
        self.assertTrue(sent.endswith(PRICE_NOTICE))
        self.assertEqual(result.caption, sent)


class ApplyPriceNoticeCommandTests(TestCase):
    def test_appends_once_and_leaves_empty_descriptions_alone(self):
        filled = Category.objects.create(name="a", telegram_message_description="hello")
        empty = Category.objects.create(name="b", telegram_message_description="")
        call_command("apply_price_notice", stdout=StringIO())
        call_command("apply_price_notice", stdout=StringIO())
        filled.refresh_from_db()
        empty.refresh_from_db()
        self.assertEqual(filled.telegram_message_description, f"hello\n\n{PRICE_NOTICE}")
        self.assertEqual(empty.telegram_message_description, "")


from types import SimpleNamespace

from PIL import Image

from price_publisher.services import special_offer_renderer as sor


class DoublePriceBannerLayoutTests(TestCase):
    """Both prices must land inside their own pill, whatever the artwork size."""

    def _render(self, trade_type, cash, account, notes=""):
        spt = SimpleNamespace(trade_type=trade_type, slug="", name="x", is_double_price=True, description="")
        ph = SimpleNamespace(cash_price=cash, account_price=account, price=cash, notes=notes)
        buf = sor.render_double_price_board(special_price_type=spt, price_history=ph).stream
        return Image.open(buf).convert("RGB")

    def _ink_box(self, img, y_ratio, base):
        """Bounding box of pixels that differ from the artwork inside one pill's number slot."""
        w, h = img.size
        left, right = (round(r * w) for r in sor.DOUBLE_SLOT_X_RATIO)
        cy = round(y_ratio * h)
        half = round(h * 0.045)
        box = []
        for y in range(cy - half, cy + half):
            for x in range(left, right):
                a, b = img.getpixel((x, y)), base.getpixel((x, y))
                if sum(abs(p - q) for p, q in zip(a, b)) > 120:
                    box.append((x, y))
        return (min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)) if box else None

    def test_numbers_sit_inside_their_pills_and_are_fully_visible(self):
        for trade_type, bg in (("buy", sor.LEGACY_DOUBLE_BUY_BACKGROUND), ("sell", sor.LEGACY_DOUBLE_SELL_BACKGROUND)):
            base = sor._open_background(sor._resolve_double_price_background_path(bg)).convert("RGB")
            img = self._render(trade_type, 346000, 21300)
            w, h = img.size
            left, right = (round(r * w) for r in sor.DOUBLE_SLOT_X_RATIO)
            for y_ratio in (sor.DOUBLE_ACCOUNT_Y_RATIO, sor.DOUBLE_CASH_Y_RATIO):
                box = self._ink_box(img, y_ratio, base)
                self.assertIsNotNone(box, (trade_type, y_ratio))
                self.assertGreaterEqual(box[0], left)
                self.assertLessEqual(box[2], right)
                cy = y_ratio * h
                self.assertLess(abs((box[1] + box[3]) / 2 - cy), h * 0.012)

    def test_long_number_shrinks_to_fit_the_slot(self):
        base = sor._open_background(sor._resolve_double_price_background_path(sor.LEGACY_DOUBLE_BUY_BACKGROUND)).convert("RGB")
        img = self._render("buy", 123456789012, 99999999999)
        left, right = (round(r * img.width) for r in sor.DOUBLE_SLOT_X_RATIO)
        box = self._ink_box(img, sor.DOUBLE_CASH_Y_RATIO, base)
        self.assertGreaterEqual(box[0], left)
        self.assertLessEqual(box[2], right)
