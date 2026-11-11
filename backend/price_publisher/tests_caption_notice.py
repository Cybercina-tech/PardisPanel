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
