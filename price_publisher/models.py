from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


class PriceTemplate(models.Model):
    """Configurable assets used when rendering Telegram price images."""

    class TemplateType(models.TextChoices):
        DEFAULT = "default", "Default"
        CATEGORY = "category", "Category"
        SPECIAL = "special", "Special Price"

    name = models.CharField(max_length=150)
    template_type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        default=TemplateType.DEFAULT,
    )

    category = models.OneToOneField(
        "category.Category",
        on_delete=models.CASCADE,
        related_name="price_template",
        null=True,
        blank=True,
    )
    special_price_type = models.OneToOneField(
        "special_price.SpecialPriceType",
        on_delete=models.CASCADE,
        related_name="price_template",
        null=True,
        blank=True,
    )

    background_image = models.ImageField(
        upload_to="price_templates/backgrounds/",
        help_text="Background used for the rendered price image.",
    )
    logo_image = models.ImageField(
        upload_to="price_templates/logos/",
        null=True,
        blank=True,
        help_text="Logo positioned on the rendered image (optional).",
    )
    watermark_image = models.ImageField(
        upload_to="price_templates/watermarks/",
        null=True,
        blank=True,
        help_text="Watermark placed near the bottom of the rendered image (optional).",
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Template"
        verbose_name_plural = "Price Templates"
        ordering = ["name"]

    def __str__(self) -> str:
        label = self.name
        if self.template_type == self.TemplateType.CATEGORY and self.category:
            label = f"{label} (Category: {self.category.name})"
        elif self.template_type == self.TemplateType.SPECIAL and self.special_price_type:
            label = f"{label} (Special: {self.special_price_type.name})"
        elif self.template_type == self.TemplateType.DEFAULT:
            label = f"{label} (Default)"
        return label

    def clean(self) -> None:
        super().clean()

        if self.template_type == self.TemplateType.CATEGORY:
            if not self.category:
                raise ValidationError("Category templates must be linked to a category.")
            if self.special_price_type:
                raise ValidationError("Category templates cannot reference a special price type.")
        elif self.template_type == self.TemplateType.SPECIAL:
            if not self.special_price_type:
                raise ValidationError("Special templates must be linked to a special price type.")
            if self.category:
                raise ValidationError("Special templates cannot reference a category.")
        else:  # default template
            if self.category or self.special_price_type:
                raise ValidationError("Default templates cannot reference specific categories or special prices.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


