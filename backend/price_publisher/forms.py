from __future__ import annotations

from django import forms

from price_publisher.models import PriceTemplate


class PriceTemplateForm(forms.ModelForm):
    class Meta:
        model = PriceTemplate
        fields = [
            "name",
            "template_type",
            "category",
            "special_price_type",
            "background_image",
            "logo_image",
            "watermark_image",
            "is_active",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["special_price_type"].required = False
        self.fields["notes"].widget = forms.Textarea(attrs={"rows": 3})

        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault("class", "form-control")
            else:
                widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned_data = super().clean()
        template_type = cleaned_data.get("template_type")
        category = cleaned_data.get("category")
        special_price_type = cleaned_data.get("special_price_type")

        if template_type == PriceTemplate.TemplateType.CATEGORY and not category:
            self.add_error("category", "Select the category this template belongs to.")
        if template_type == PriceTemplate.TemplateType.SPECIAL and not special_price_type:
            self.add_error(
                "special_price_type",
                "Select the special price type this template belongs to.",
            )
        if template_type == PriceTemplate.TemplateType.DEFAULT:
            cleaned_data["category"] = None
            cleaned_data["special_price_type"] = None

        return cleaned_data


