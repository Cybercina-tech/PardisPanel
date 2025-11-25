import io
import json
import os
from typing import Any

from django import forms
from django.conf import settings
from django.core.files.images import get_image_dimensions
from django.core.validators import FileExtensionValidator
from PIL import Image

from .admin_validators import validate_template_config
from .admin_widgets import AdminImagePreviewWidget, TemplateConfigWidget
from .models import Template


MAX_IMAGE_BYTES = getattr(settings, "TEMPLATE_EDITOR_MAX_IMAGE_BYTES", 8 * 1024 * 1024)  # 8MB default
ALLOWED_IMAGE_EXTENSIONS = ("png", "jpg", "jpeg", "webp")


class TemplateAdminForm(forms.ModelForm):
    """Admin form with enhanced validation and widgets."""

    config = forms.JSONField(required=False, widget=TemplateConfigWidget)

    class Meta:
        model = Template
        fields = (
            "name",
            "category",
            "special_price_type",
            "image",
            "config",
        )
        widgets = {
            "image": AdminImagePreviewWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_warnings: list[str] = []

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        if image.size and image.size > MAX_IMAGE_BYTES:
            raise forms.ValidationError(
                f"Image is too large ({image.size / (1024 * 1024):.1f} MB). "
                f"Maximum allowed size is {MAX_IMAGE_BYTES / (1024 * 1024):.0f} MB."
            )

        ext = os.path.splitext(image.name)[1].lower().replace(".", "")
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise forms.ValidationError(
                f"Unsupported image format '.{ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
            )

        return image

    def clean_config(self):
        config = self.cleaned_data.get("config") or {"fields": {}}
        image = self.cleaned_data.get("image") or self.instance.image
        dimensions = self._get_image_size(image)
        warnings = validate_template_config(config, image_size=dimensions)
        self.config_warnings = warnings
        return config

    def _get_image_size(self, image_field) -> tuple[int, int] | None:
        if not image_field:
            return None
        try:
            if hasattr(image_field, "width") and hasattr(image_field, "height"):
                return image_field.width, image_field.height
            if hasattr(image_field, "path"):
                return get_image_dimensions(image_field)
            with Image.open(image_field) as img:
                return img.size
        except Exception:
            return None


class TemplateConfigImportForm(forms.Form):
    """Form used by the import admin view."""

    MERGE_CHOICES = (
        ("replace", "Replace existing config"),
        ("merge", "Merge and keep missing fields"),
    )

    config_file = forms.FileField(
        help_text="Upload JSON exported from this admin. Max 512 KB.",
        validators=[FileExtensionValidator(["json"])],
    )
    merge_strategy = forms.ChoiceField(choices=MERGE_CHOICES, initial="replace")
    dry_run = forms.BooleanField(
        required=False,
        help_text="Validate and show changes without saving.",
    )

    def __init__(self, *args, **kwargs):
        self.parsed_config: dict[str, Any] | None = None
        self.config_warnings: list[str] = []
        super().__init__(*args, **kwargs)

    def clean_config_file(self):
        file = self.cleaned_data["config_file"]
        if file.size > 512 * 1024:
            raise forms.ValidationError("Config file exceeds 512 KB limit.")
        content = file.read().decode("utf-8")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"Invalid JSON: {exc}") from exc
        warnings = validate_template_config(data)
        self.parsed_config = data
        self.config_warnings = warnings
        file.seek(0)
        return file

