from django.contrib import admin
from django.utils.translation import gettext_lazy as _
import json

from .models import Template


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "special_price_type", "created_at", "updated_at")
    list_filter = ("category", "special_price_type", "created_at", "updated_at")
    search_fields = ("name", "category__name", "special_price_type__name")
    readonly_fields = ("created_at", "updated_at", "config_display")
    ordering = ("-created_at",)

    fieldsets = (
        ("Template Details", {
            "fields": ("name", "category", "special_price_type", "image")
        }),
        ("Configuration", {
            "fields": ("config_display",),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def config_display(self, obj):
        """Display formatted JSON config."""
        if obj.config:
            from django.utils.safestring import mark_safe
            return mark_safe(f"<pre>{json.dumps(obj.config, indent=2)}</pre>")
        return "No configuration"
    config_display.short_description = "Configuration"

