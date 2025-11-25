import json
from typing import Any

from django.contrib.admin.widgets import AdminTextareaWidget
from django.forms.widgets import ClearableFileInput
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class TemplateConfigWidget(AdminTextareaWidget):
    """Textarea widget with helper UI for managing template config JSON."""

    template_name = "django/forms/widgets/textarea.html"

    class Media:
        css = {
            "all": ("template_editor/admin/template_admin.css",),
        }
        js = ("template_editor/admin/template_admin.js",)

    def format_value(self, value: Any) -> str:
        if value in (None, ""):
            return json.dumps({"fields": {}}, indent=2)

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value

        try:
            return json.dumps(value, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(value)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault("class", "")
        attrs["class"] += " template-config-json"
        rendered = super().render(name, value, attrs, renderer)
        textarea_id = attrs.get("id", f"id_{name}")

        helper = format_html(
            (
                '<div class="template-config-helper" data-config-source="{id}">'
                "<div class=\"template-config-toolbar\">"
                '<button type="button" class="button button-small js-add-field">Add field</button>'
                '<button type="button" class="button button-small js-sort-fields">Sort A→Z</button>'
                '<button type="button" class="button button-small js-format-json">Format JSON</button>'
                "</div>"
                '<div class="template-config-table-wrapper">'
                "<table class=\"template-config-table\">"
                "<thead><tr>"
                "<th>Field</th><th>X</th><th>Y</th><th>Size</th><th>Color</th>"
                "<th>Align</th><th>Max width</th><th></th>"
                "</tr></thead>"
                "<tbody></tbody>"
                "</table>"
                "</div>"
                "</div>"
            ),
            id=textarea_id,
        )

        return mark_safe(f'<div class="template-config-widget">{rendered}{helper}</div>')


class AdminImagePreviewWidget(ClearableFileInput):
    """Image widget with inline preview and reset button."""

    class Media:
        css = {
            "all": ("template_editor/admin/template_admin.css",),
        }
        js = ("template_editor/admin/template_admin.js",)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs.setdefault("class", "")
        attrs["class"] += " template-image-input"
        rendered = super().render(name, value, attrs, renderer)

        if value and hasattr(value, "url"):
            preview = format_html(
                '<img src="{}" alt="Current image" class="template-image-thumb"/>',
                value.url,
            )
        else:
            preview = '<div class="template-image-thumb template-image-thumb--empty">No image</div>'

        return mark_safe(
            '<div class="template-image-widget">'
            f'{preview}<div class="template-image-input-wrapper">{rendered}</div>'
            "</div>"
        )

