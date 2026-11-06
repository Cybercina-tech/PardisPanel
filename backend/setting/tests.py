from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APITestCase

from core.prices_webhook import notify_prices_webhook
from setting.models import SiteSettings
from setting.serializers import SiteSettingsSerializer


class SiteSettingsUiFontValidationTest(TestCase):
    def test_empty_ui_fonts_allowed(self):
        s = SiteSettingsSerializer(
            instance=SiteSettings.load(),
            data={
                "ui_font_filename_rtl": "",
                "ui_font_filename_ltr": "",
            },
            partial=True,
        )
        self.assertTrue(s.is_valid(), s.errors)

    def test_unknown_font_rejected(self):
        s = SiteSettingsSerializer(
            instance=SiteSettings.load(),
            data={"ui_font_filename_rtl": "definitely-missing-file-xyz.ttf"},
            partial=True,
        )
        self.assertFalse(s.is_valid())
        self.assertIn("ui_font_filename_rtl", s.errors)


class SiteSettingsSafeImageSerializationTest(TestCase):
    def test_missing_logo_file_serializes_as_null(self):
        SiteSettings.objects.get_or_create(pk=1, defaults={"site_name": "Test"})
        SiteSettings.objects.filter(pk=1).update(logo="branding/__missing_logo_for_test__.png")
        cache.delete("site_settings")
        obj = SiteSettings.objects.get(pk=1)
        request = MagicMock()
        request.build_absolute_uri = lambda uri: "http://localhost:8000" + uri
        ser = SiteSettingsSerializer(obj, context={"request": request})
        self.assertIsNone(ser.data.get("logo"))
        SiteSettings.objects.filter(pk=1).update(logo="")
        cache.delete("site_settings")


class SiteSettingsWebhookSerializationTests(TestCase):
    def setUp(self):
        cache.delete("site_settings")
        s = SiteSettings.load()
        s.prices_webhook_url = "https://example.com/secret"
        s.save()

    def test_webhook_hidden_without_super_admin(self):
        obj = SiteSettings.objects.get(pk=1)
        req = MagicMock()
        req.user = MagicMock()
        req.user.is_authenticated = True
        req.user.is_superuser = False
        req.user.role = "management"
        req.user.username = "m"
        data = SiteSettingsSerializer(obj, context={"request": req}).data
        self.assertNotIn("prices_webhook_url", data)

    def test_webhook_visible_for_super_admin(self):
        obj = SiteSettings.objects.get(pk=1)
        req = MagicMock()
        req.user = MagicMock()
        req.user.is_authenticated = True
        req.user.is_superuser = True
        req.user.username = "sa"
        data = SiteSettingsSerializer(obj, context={"request": req}).data
        self.assertEqual(data.get("prices_webhook_url"), "https://example.com/secret")


class PricesWebhookNotifyTests(TestCase):
    def setUp(self):
        cache.delete("site_settings")

    @patch("core.prices_webhook.threading.Thread")
    def test_notify_skips_when_url_empty(self, mock_thread):
        s = SiteSettings.load()
        s.prices_webhook_url = ""
        s.save()
        notify_prices_webhook("x")
        mock_thread.assert_not_called()

    @patch("core.prices_webhook.threading.Thread")
    def test_notify_starts_thread_when_url_set(self, mock_thread):
        s = SiteSettings.load()
        s.prices_webhook_url = "https://httpbin.org/post"
        s.save()
        mock_inst = MagicMock()
        mock_thread.return_value = mock_inst
        notify_prices_webhook("change_price.single")
        mock_thread.assert_called_once()
        mock_inst.start.assert_called_once()


class PublicPricesApiTests(APITestCase):
    def test_get_public_prices_no_auth_returns_200(self):
        r = self.client.get("/api/public/prices/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("generated_at", body)
        self.assertIn("categories", body)
        self.assertIn("special_prices", body)
