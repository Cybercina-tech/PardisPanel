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
