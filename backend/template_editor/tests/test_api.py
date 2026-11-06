import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from PIL import Image
from rest_framework.exceptions import ValidationError as DRFValidationError

from category.models import Category, Currency, PriceType
from template_editor.api_views import _validate_template_price_bindings
from template_editor.models import Template
from template_editor.render_config_json import (
    _design_to_actual_font_scale,
    render_template_from_config_json,
)
from template_editor.utils import (
    DEFAULT_LATIN_FONT_FILENAME,
    DEFAULT_RTL_FONT_FILENAME,
    font_script_hint,
    resolve_font_filename_for_text,
)


class TemplateBindingValidationTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="EUR")
        self.other_category = Category.objects.create(name="USDT")
        self.eur, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro"})
        self.irr, _ = Currency.objects.get_or_create(code="IRR", defaults={"name": "Rial"})
        self.gbp, _ = Currency.objects.get_or_create(code="GBP", defaults={"name": "Pound"})
        self.valid_pt = PriceType.objects.create(
            category=self.category,
            name="Buy EUR",
            source_currency=self.eur,
            target_currency=self.irr,
            trade_type="buy",
        )
        self.invalid_pt = PriceType.objects.create(
            category=self.other_category,
            name="Sell GBP",
            source_currency=self.gbp,
            target_currency=self.irr,
            trade_type="sell",
        )
        self.template = Template.objects.create(name="eur-template", category=self.category)

    def test_accepts_config_without_price_binding_draft(self):
        _validate_template_price_bindings(
            self.template,
            {
                "widgets": [
                    {
                        "id": "a1",
                        "type": "text",
                        "x": "10%",
                        "y": "10%",
                        "width": "20%",
                        "height": "10%",
                        "style": {},
                    }
                ]
            },
        )

    def test_rejects_price_binding_from_another_category(self):
        with self.assertRaises(DRFValidationError):
            _validate_template_price_bindings(
                self.template,
                {
                    "widgets": [
                        {
                            "id": "a1",
                            "type": "text",
                            "x": "10%",
                            "y": "10%",
                            "width": "20%",
                            "height": "10%",
                            "style": {"priceTypeId": self.invalid_pt.id},
                        }
                    ]
                },
            )

    def test_accepts_valid_category_price_binding(self):
        _validate_template_price_bindings(
            self.template,
            {
                "widgets": [
                    {
                        "id": "a1",
                        "type": "text",
                        "x": "10%",
                        "y": "10%",
                        "width": "20%",
                        "height": "10%",
                        "style": {"priceTypeId": self.valid_pt.id},
                    }
                ]
            },
        )


class RenderConfigJsonFontScaleTest(TestCase):
    """Font size in config_json is in template canvas px; PIL must scale when image size differs."""

    def test_design_to_actual_font_scale_uses_minimum_axis_ratio(self):
        self.assertAlmostEqual(
            _design_to_actual_font_scale(1080, 1080, 2160, 2160),
            2.0,
        )
        self.assertAlmostEqual(
            _design_to_actual_font_scale(1080, 2000, 2160, 2000),
            min(2160 / 1080.0, 2000 / 2000.0),
        )
        self.assertEqual(_design_to_actual_font_scale(0, 1080, 100, 100), 1.0)

    @patch("template_editor.render_config_json.draw_text_field")
    def test_font_size_scales_when_background_exceeds_canvas_metadata(self, mock_draw):
        path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        try:
            Image.new("RGB", (2160, 2160), color=(20, 20, 20)).save(path)
            tpl = type(
                "Tpl",
                (),
                {
                    "canvas_width": 1080,
                    "canvas_height": 1080,
                    "config_json": {},
                    "image": type("Img", (), {"path": path})(),
                },
            )()
            cfg = {
                "widgets": [
                    {
                        "id": "w1",
                        "type": "text",
                        "x": "10%",
                        "y": "10%",
                        "width": "80%",
                        "height": "25%",
                        "style": {"fontSize": 50},
                        "content": "177,777",
                    }
                ]
            }
            render_template_from_config_json(tpl, {}, config_json_override=cfg)
            mock_draw.assert_called_once()
            self.assertEqual(mock_draw.call_args.kwargs.get("size"), 100)
        finally:
            Path(path).unlink(missing_ok=True)

    @patch("template_editor.render_config_json.draw_text_field")
    def test_font_size_unscaled_when_canvas_matches_image_pixels(self, mock_draw):
        path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        try:
            Image.new("RGB", (1080, 1080), color=(0, 0, 0)).save(path)
            tpl = type(
                "Tpl",
                (),
                {
                    "canvas_width": 1080,
                    "canvas_height": 1080,
                    "config_json": {},
                    "image": type("Img", (), {"path": path})(),
                },
            )()
            cfg = {
                "widgets": [
                    {
                        "id": "w1",
                        "type": "text",
                        "x": "5%",
                        "y": "5%",
                        "width": "90%",
                        "height": "20%",
                        "style": {"fontSize": 77},
                        "content": "test",
                    }
                ]
            }
            render_template_from_config_json(tpl, {}, config_json_override=cfg)
            mock_draw.assert_called_once()
            self.assertEqual(mock_draw.call_args.kwargs.get("size"), 77)
        finally:
            Path(path).unlink(missing_ok=True)


class TemplateEditorFontResolutionTest(TestCase):
    def test_font_script_hint_bundled_vf(self):
        self.assertEqual(font_script_hint(DEFAULT_RTL_FONT_FILENAME), "both")
        self.assertEqual(font_script_hint(DEFAULT_LATIN_FONT_FILENAME), "ltr")

    def test_resolve_rtl_font_latin_only_content_switches_to_latin(self):
        out = resolve_font_filename_for_text(DEFAULT_RTL_FONT_FILENAME, "177,777")
        self.assertEqual(out, DEFAULT_LATIN_FONT_FILENAME)

    def test_resolve_rtl_font_kept_for_persian(self):
        out = resolve_font_filename_for_text(DEFAULT_RTL_FONT_FILENAME, "سلام")
        self.assertEqual(out, DEFAULT_RTL_FONT_FILENAME)

    def test_resolve_latin_font_persian_content_switches_to_rtl(self):
        out = resolve_font_filename_for_text(DEFAULT_LATIN_FONT_FILENAME, "سلام")
        self.assertEqual(out, DEFAULT_RTL_FONT_FILENAME)
