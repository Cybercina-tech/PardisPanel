from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from category.models import Category
from template_editor.headless_context import build_headless_context, resolve_widget_content
from template_editor.models import Template
from template_editor.render_tokens import (
    issue_headless_render_token,
    load_headless_render_context,
    store_headless_render_context,
    verify_headless_render_token,
)


class HeadlessRenderTokenTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_token_round_trip(self):
        context_id = store_headless_render_context({"template_id": 5, "widgets": []})
        token = issue_headless_render_token(5, context_id)
        parsed = verify_headless_render_token(token)
        self.assertEqual(parsed["template_id"], 5)
        self.assertEqual(parsed["context_id"], context_id)

    def test_invalid_token_raises(self):
        with self.assertRaises(ValueError):
            verify_headless_render_token("not-a-valid-token")


class HeadlessContextTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Test Cat")
        self.template = Template.objects.create(
            name="ctx-template",
            category=self.category,
            canvas_width=1080,
            canvas_height=1080,
            config_json={
                "backgroundColor": "#112233",
                "widgets": [
                    {
                        "id": "w1",
                        "type": "text",
                        "x": "10%",
                        "y": "20%",
                        "width": "40%",
                        "height": "8%",
                        "style": {"priceTypeId": 7, "bindingKey": "price_type__7"},
                    },
                    {
                        "id": "w2",
                        "type": "date",
                        "x": "10%",
                        "y": "50%",
                        "width": "40%",
                        "height": "8%",
                        "style": {"dateKey": "date_fa"},
                    },
                ],
            },
        )

    def test_build_headless_context_resolves_widgets(self):
        dynamic_data = {
            "price_type__7": "1,234,567",
            "date_fa": "۱۰ خرداد ۱۴۰۴",
        }
        ctx = build_headless_context(self.template, dynamic_data)
        self.assertEqual(ctx["template_id"], self.template.pk)
        self.assertEqual(ctx["canvas_width"], 1080)
        self.assertEqual(ctx["background_color"], "#112233")
        self.assertEqual(len(ctx["widgets"]), 2)
        self.assertEqual(ctx["widgets"][0]["content"], "1,234,567")
        self.assertEqual(ctx["widgets"][1]["content"], "۱۰ خرداد ۱۴۰۴")
        self.assertIn("price_type__7", ctx["price_binding_map"])
        self.assertTrue(ctx["fonts"] or isinstance(ctx["fonts"], list))

    def test_resolve_widget_content_uses_binding(self):
        widget = {
            "type": "text",
            "style": {"priceTypeId": 3},
        }
        text = resolve_widget_content(widget, {"price_type__3": "999"})
        self.assertEqual(text, "999")


class HeadlessRenderContextAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.category = Category.objects.create(name="API Cat")
        self.template = Template.objects.create(
            name="api-template",
            category=self.category,
            config_json={"backgroundColor": "#fff", "widgets": []},
        )

    def test_context_api_returns_payload_for_valid_token(self):
        ctx = build_headless_context(self.template, {"date_fa": "today"})
        context_id = store_headless_render_context(ctx)
        token = issue_headless_render_token(self.template.pk, context_id)
        url = reverse("api-template-editor-headless-render-context")
        response = self.client.get(url, {"token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["template_id"], self.template.pk)
        self.assertEqual(response.data["background_color"], "#fff")

    def test_context_api_rejects_missing_token(self):
        url = reverse("api-template-editor-headless-render-context")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_context_api_rejects_expired_context(self):
        token = issue_headless_render_token(self.template.pk, "missing-context-id")
        url = reverse("api-template-editor-headless-render-context")
        response = self.client.get(url, {"token": token})
        self.assertEqual(response.status_code, 404)

    def test_load_context_after_store(self):
        ctx = {"template_id": 1, "widgets": []}
        context_id = store_headless_render_context(ctx)
        loaded = load_headless_render_context(context_id)
        self.assertEqual(loaded, ctx)
