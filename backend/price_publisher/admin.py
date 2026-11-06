import io
import os

from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .admin_forms import PriceTemplateAdminForm
from .models import PriceTemplate

BADGE_STYLE = (
    "display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;"
    "text-transform:uppercase;letter-spacing:0.05em;"
)


@admin.register(PriceTemplate)
class PriceTemplateAdmin(admin.ModelAdmin):
    form = PriceTemplateAdminForm
    list_display = (
        "preview_thumb",
        "name",
        "template_type",
        "target_label",
        "is_active",
        "updated_at",
    )
    list_display_links = ("preview_thumb", "name")
    list_filter = ("template_type", "is_active", "category", "special_price_type")
    search_fields = ("name", "notes", "category__name", "special_price_type__name")
    readonly_fields = ("created_at", "updated_at", "asset_preview")
    autocomplete_fields = ("category", "special_price_type")
    actions = ("duplicate_templates", "export_assets")
    ordering = ("name",)

    fieldsets = (
        (_("Template"), {"fields": ("name", "template_type", "is_active", "notes")}),
        (
            _("Assignment"),
            {
                "fields": ("category", "special_price_type"),
                "description": _("Category and special assignments are mutually exclusive."),
            },
        ),
        (
            _("Assets"),
            {
                "fields": ("background_image", "logo_image", "watermark_image", "asset_preview"),
                "classes": ("wide",),
            },
        ),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category", "special_price_type")

    def preview_thumb(self, obj):
        if not obj.background_image:
            return _("No image")
        return format_html(
            '<img src="{}" alt="{}" class="admin-template-thumb"/>',
            obj.background_image.url,
            obj.name,
        )

    preview_thumb.short_description = _("Preview")

    def target_label(self, obj):
        if obj.category:
            return format_html(
                '<span style="{}background:#e8f5e9;color:#2e7d32;">{}</span>',
                BADGE_STYLE,
                obj.category.name,
            )
        if obj.special_price_type:
            return format_html(
                '<span style="{}background:#f3e5f5;color:#6a1b9a;">{}</span>',
                BADGE_STYLE,
                obj.special_price_type.name,
            )
        return _("Default")

    target_label.short_description = _("Target")

    def asset_preview(self, obj):
        if not obj.pk:
            return _("Assets preview will be available after saving.")
        images = [
            ( _("Background"), obj.background_image),
            ( _("Logo"), obj.logo_image),
            ( _("Watermark"), obj.watermark_image),
        ]
        rows = [
            format_html(
                "<div><strong>{label}:</strong><br><img src='{url}' class='template-image-thumb' alt='{label}'></div>",
                label=label,
                url=image.url,
            )
            for label, image in images
            if image
        ]
        if not rows:
            return _("No assets uploaded yet.")
        return format_html("<div class='asset-preview'>{}</div>", format_html_join("", "{}", ((row,) for row in rows)))

    asset_preview.short_description = _("Asset preview")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def duplicate_templates(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, _("Select templates to duplicate."), level=messages.WARNING)
            return None
        created = 0
        for template in queryset:
            duplicate = PriceTemplate(
                name=self._copy_name(template.name, created),
                template_type=template.template_type,
                category=template.category,
                special_price_type=template.special_price_type,
                is_active=False,
                notes=template.notes,
            )
            for field in ("background_image", "logo_image", "watermark_image"):
                image = getattr(template, field)
                if not image:
                    continue
                image.open("rb")
                try:
                    getattr(duplicate, field).save(
                        self._duplicate_filename(image.name),
                        ContentFile(image.read()),
                        save=False,
                    )
                finally:
                    image.close()
            duplicate.save()
            created += 1
        self.message_user(request, _(f"{created} template(s) duplicated."), level=messages.SUCCESS)

    duplicate_templates.short_description = _("Duplicate selected templates")

    def export_assets(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, _("Select templates to export."), level=messages.WARNING)
            return None
        archive = io.BytesIO()
        import zipfile

        with zipfile.ZipFile(archive, "w") as bundle:
            for template in queryset:
                for field in ("background_image", "logo_image", "watermark_image"):
                    image = getattr(template, field)
                    if not image:
                        continue
                    image.open("rb")
                    try:
                        bundle.writestr(
                            f"{slugify(template.name)}/{field}{os.path.splitext(image.name)[1]}",
                            image.read(),
                        )
                    finally:
                        image.close()
        archive.seek(0)
        response = HttpResponse(archive.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="price-template-assets.zip"'
        return response

    export_assets.short_description = _("Export assets (.zip)")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _copy_name(self, base_name, idx):
        suffix = idx + 1
        name = f"{base_name} copy {suffix}"
        while PriceTemplate.objects.filter(name=name).exists():
            suffix += 1
            name = f"{base_name} copy {suffix}"
        return name

    def _duplicate_filename(self, original_name):
        base, ext = os.path.splitext(os.path.basename(original_name))
        return f"price_templates/{slugify(base) or 'asset'}-copy{ext or '.png'}"


