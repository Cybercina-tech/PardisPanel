import os

from django import forms
from django.conf import settings

from template_editor.admin_widgets import AdminImagePreviewWidget

from .models import PriceTemplate


MAX_ASSET_BYTES = getattr(settings, "PRICE_TEMPLATE_MAX_IMAGE_BYTES", 6 * 1024 * 1024)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


class PriceTemplateAdminForm(forms.ModelForm):
    class Meta:
        model = PriceTemplate
        fields = "__all__"
        widgets = {
            "background_image": AdminImagePreviewWidget,
            "logo_image": AdminImagePreviewWidget,
            "watermark_image": AdminImagePreviewWidget,
        }

    def clean_background_image(self):
        return self._validate_image("background_image")

    def clean_logo_image(self):
        return self._validate_optional_image("logo_image")

    def clean_watermark_image(self):
        return self._validate_optional_image("watermark_image")

    def _validate_optional_image(self, field):
        image = self.cleaned_data.get(field)
        if image:
            self._validate_file(image, field)
        return image

    def _validate_image(self, field):
        image = self.cleaned_data.get(field)
        if not image:
            raise forms.ValidationError("This image is required.")
        self._validate_file(image, field)
        return image

    def _validate_file(self, image, field):
        if image.size and image.size > MAX_ASSET_BYTES:
            raise forms.ValidationError(
                f"{field.replace('_', ' ').title()} exceeds {MAX_ASSET_BYTES / (1024 * 1024):.0f} MB."
            )
        ext = os.path.splitext(image.name)[1].lower().lstrip(".")
        if ext not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                f"Unsupported format '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

