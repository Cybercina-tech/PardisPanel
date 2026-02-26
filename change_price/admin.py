import io

from django.contrib import admin, messages
from django.db.models import F, Window
from django.db.models.functions import Lag
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from template_editor.models import Template
from template_editor.utils import render_template
from core.formatting import format_price_dynamic

from .models import PriceHistory

BADGE_STYLE = (
    "display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;"
    "text-transform:uppercase;letter-spacing:0.05em;margin-right:6px;"
)


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "price_type",
        "category_badge",
        "formatted_price",
        "trend_indicator",
        "created_at",
        "notes_preview",
    )
    list_filter = (
        "price_type__category",
        "price_type__trade_type",
        "price_type__source_currency",
        "price_type__target_currency",
        "created_at",
    )
    search_fields = (
        "price_type__name",
        "price_type__category__name",
        "price_type__source_currency__code",
        "price_type__target_currency__code",
        "notes",
    )
    readonly_fields = ("created_at", "updated_at", "previous_price_display")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    actions = ("preview_with_template",)
    list_select_related = (
        "price_type",
        "price_type__category",
        "price_type__source_currency",
        "price_type__target_currency",
    )

    fieldsets = (
        (_("Price entry"), {"fields": ("price_type", "price", "notes")}),
        (
            _("Diagnostics"),
            {
                "fields": ("previous_price_display", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            previous_price=Window(
                expression=Lag("price"),
                partition_by=[F("price_type")],
                order_by=[F("created_at").asc()],
            )
        )

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    def category_badge(self, obj):
        category = obj.price_type.category
        if not category:
            return "—"
        return format_html(
            '<span style="{}background:#e8f5e9;color:#2e7d32;">{}</span>',
            BADGE_STYLE,
            category.name,
        )

    category_badge.short_description = _("Category")

    def formatted_price(self, obj):
        value = format_price_dynamic(obj.price)
        currency = f"{obj.price_type.source_currency.code}/{obj.price_type.target_currency.code}"
        return format_html('<span class="price-value">{}</span> <small>{}</small>', value, currency)

    formatted_price.short_description = _("Price")

    def trend_indicator(self, obj):
        previous = getattr(obj, "previous_price", None)
        if previous is None:
            return format_html(
                '<span style="{}background:#eceff1;color:#546e7a;">n/a</span>',
                BADGE_STYLE,
            )
        delta = obj.price - previous
        if delta == 0:
            return format_html(
                '<span style="{}background:#eceff1;color:#546e7a;">= 0</span>',
                BADGE_STYLE,
            )
        color = "#2e7d32" if delta > 0 else "#c62828"
        icon = "▲" if delta > 0 else "▼"
        return format_html(
            '<span style="{}background:{};color:#fff;">{icon} {value}</span>',
            BADGE_STYLE,
            color,
            icon=icon,
            value=format_price_dynamic(abs(delta)) if delta >= 0 else "-" + format_price_dynamic(abs(delta)),
        )

    trend_indicator.short_description = _("Change")

    def notes_preview(self, obj):
        if not obj.notes:
            return "—"
        snippet = (obj.notes[:60] + "…") if len(obj.notes) > 60 else obj.notes
        return snippet

    notes_preview.short_description = _("Notes")

    def previous_price_display(self, obj):
        previous = getattr(obj, "previous_price", None)
        if previous is None:
            return _("No previous price.")
        delta = obj.price - previous
        prev_str = format_price_dynamic(previous)
        delta_str = ("+" if delta >= 0 else "-") + format_price_dynamic(abs(delta))
        return f"Previous: {prev_str} · Δ {delta_str}"

    previous_price_display.short_description = _("Previous price")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def preview_with_template(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, _("Select at least one record."), level=messages.WARNING)
            return None
        category_ids = queryset.values_list("price_type__category_id", flat=True).distinct()
        if category_ids.count() > 1:
            self.message_user(
                request,
                _("Select prices belonging to a single category to preview."),
                level=messages.WARNING,
            )
            return None
        category_id = category_ids.first()
        template = self._resolve_template(category_id)
        if not template:
            self.message_user(
                request,
                _("No template is linked to this category yet."),
                level=messages.WARNING,
            )
            return None

        data = self._build_dynamic_payload(template, queryset)
        image = render_template(template, data)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="image/png")
        filename = f"{template.name}_preview.png".replace(" ", "_")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    preview_with_template.short_description = _("Preview template with these prices")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_template(self, category_id):
        if not category_id:
            return Template.objects.filter(category__isnull=True, special_price_type__isnull=True).order_by("-updated_at").first()
        template = (
            Template.objects.filter(category_id=category_id).order_by("-updated_at").first()
        )
        if template:
            return template
        return Template.objects.filter(category__isnull=True, special_price_type__isnull=True).order_by("-updated_at").first()

    def _build_dynamic_payload(self, template, queryset):
        now = timezone.localtime()
        payload = {
            "english_date": now.strftime("%Y-%m-%d %H:%M"),
            "persian_date": now.strftime("%Y/%m/%d"),
            "category_name": template.category.name if template.category else "",
        }
        fields = (template.config or {}).get("fields", {})
        buy_entries = [obj for obj in queryset if obj.price_type.trade_type == "buy"]
        sell_entries = [obj for obj in queryset if obj.price_type.trade_type == "sell"]
        fallback_entries = list(queryset)

        for field_name in fields.keys():
            key_lower = field_name.lower()
            entry = None
            if "buy" in key_lower and buy_entries:
                entry = buy_entries.pop(0)
            elif "sell" in key_lower and sell_entries:
                entry = sell_entries.pop(0)
            elif "price" in key_lower and fallback_entries:
                entry = fallback_entries.pop(0)

            if entry:
                payload[field_name] = self._format_price(entry)
            else:
                payload.setdefault(field_name, field_name.replace("_", " ").title())
        return payload

    def _format_price(self, entry: PriceHistory) -> str:
        value = format_price_dynamic(entry.price)
        source = entry.price_type.source_currency.code
        target = entry.price_type.target_currency.code
        return f"{value} {source}/{target}"