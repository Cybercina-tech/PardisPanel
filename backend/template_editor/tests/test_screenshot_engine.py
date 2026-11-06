from io import BytesIO
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from PIL import Image

from category.models import Category
from template_editor.models import Template
from template_editor.services.screenshot_engine import (
    ScreenshotEngineError,
    _price_fingerprint,
    generate_template_screenshot,
    shutdown_browser,
)


class ScreenshotEngineTests(TestCase):
    def setUp(self):
        cache.clear()
        shutdown_browser()
        self.category = Category.objects.create(name="Shot Cat")
        self.template = Template.objects.create(
            name="shot-template",
            category=self.category,
            canvas_width=400,
            canvas_height=300,
            config_json={
                "backgroundColor": "#000000",
                "widgets": [
                    {
                        "id": "t1",
                        "type": "text",
                        "x": "10%",
                        "y": "10%",
                        "width": "80%",
                        "height": "20%",
                        "content": "Hello",
                    }
                ],
            },
        )

    def tearDown(self):
        shutdown_browser()
        cache.clear()

    def test_price_fingerprint_stable(self):
        data = {"price_type__1": "100"}
        fp1 = _price_fingerprint(self.template, data)
        fp2 = _price_fingerprint(self.template, data)
        self.assertEqual(fp1, fp2)

    @override_settings(SCREENSHOT_CACHE_TTL=300)
    @patch("template_editor.services.screenshot_engine._issue_render_url")
    @patch("template_editor.services.screenshot_engine._get_browser")
    def test_generate_uses_cache_on_second_call(self, mock_browser, mock_url):
        png = BytesIO()
        Image.new("RGB", (400, 300), color=(255, 0, 0)).save(png, format="PNG")
        png_bytes = png.getvalue()

        page = MagicMock()
        page.locator.return_value.screenshot.return_value = png_bytes
        context = MagicMock()
        context.new_page.return_value = page
        browser = MagicMock()
        browser.new_context.return_value = context
        mock_browser.return_value = browser
        mock_url.return_value = "http://example.test/headless-render/1?token=x"

        dynamic_data = {"price_type__1": "500"}
        first = generate_template_screenshot(
            template_id=self.template.pk,
            dynamic_data=dynamic_data,
        )
        second = generate_template_screenshot(
            template_id=self.template.pk,
            dynamic_data=dynamic_data,
        )
        self.assertEqual(first, second)
        self.assertEqual(mock_url.call_count, 1)

    @override_settings(SCREENSHOT_CACHE_TTL=300, PLAYWRIGHT_MAX_CONCURRENT=1)
    @patch("template_editor.services.screenshot_engine._issue_render_url")
    @patch("template_editor.services.screenshot_engine._get_browser")
    def test_generate_screenshot_success(self, mock_browser, mock_url):
        png = BytesIO()
        Image.new("RGB", (400, 300), color=(0, 255, 0)).save(png, format="PNG")
        png_bytes = png.getvalue()

        page = MagicMock()
        page.locator.return_value.screenshot.return_value = png_bytes
        context = MagicMock()
        context.new_page.return_value = page
        browser = MagicMock()
        browser.new_context.return_value = context
        mock_browser.return_value = browser
        mock_url.return_value = "http://example.test/headless-render/1?token=x"

        result = generate_template_screenshot(
            template_id=self.template.pk,
            dynamic_data={"price_type__1": "100"},
        )
        self.assertTrue(result.startswith(b"\x89PNG"))
        page.goto.assert_called_once()
        page.wait_for_selector.assert_called()

    @patch("template_editor.services.screenshot_engine._get_browser")
    def test_generate_raises_on_playwright_failure(self, mock_browser):
        browser = MagicMock()
        browser.new_context.side_effect = RuntimeError("browser crashed")
        mock_browser.return_value = browser

        with self.assertRaises(ScreenshotEngineError):
            generate_template_screenshot(
                template_id=self.template.pk,
                dynamic_data={"price_type__1": "100"},
            )
