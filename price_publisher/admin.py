from django.contrib import admin

from price_publisher.models import PriceTemplate


@admin.register(PriceTemplate)
class PriceTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "template_type",
        "category",
        "special_price_type",
        "is_active",
        "updated_at",
    )
    list_filter = ("template_type", "is_active")
    search_fields = ("name", "notes")


