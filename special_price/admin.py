import io
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import F, Window
from django.db.models.functions import Lag
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from template_editor.models import Template
from template_editor.utils import render_template

from .models import SpecialPriceHistory, SpecialPriceType

BADGE_STYLE = (
    "display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;"
    "text-transform:uppercase;letter-spacing:0.05em;margin-right:6px;"
)


@admin.register(SpecialPriceType)
class SpecialPriceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_currency', 'target_currency', 'trade_type', 'slug', 'created_at')
    list_filter = ('source_currency', 'target_currency', 'trade_type', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'source_currency', 'target_currency', 'trade_type')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SpecialPriceHistory)
class SpecialPriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'special_price_type',
        'formatted_price',
        'trend_indicator',
        'created_at',
        'notes_preview',
    )
    list_filter = (
        'special_price_type',
        'special_price_type__trade_type',
        'created_at',
    )
    search_fields = (
        'special_price_type__name',
        'special_price_type__source_currency__code',
        'special_price_type__target_currency__code',
        'notes',
    )
    readonly_fields = ('created_at', 'updated_at', 'previous_price_display')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    actions = ('preview_with_template',)
    list_select_related = (
        'special_price_type',
        'special_price_type__source_currency',
        'special_price_type__target_currency',
    )
    
    fieldsets = (
        ('Price Information', {
            'fields': ('special_price_type', 'price', 'notes')
        }),
        ('Diagnostics', {
            'fields': ('previous_price_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            previous_price=Window(
                expression=Lag('price'),
                partition_by=[F('special_price_type')],
                order_by=[F('created_at').asc()],
            )
        )

    def formatted_price(self, obj):
        value = f"{obj.price:,.2f}"
        pair = f"{obj.special_price_type.source_currency.code}/{obj.special_price_type.target_currency.code}"
        return format_html('<span class="price-value">{}</span> <small>{}</small>', value, pair)

    formatted_price.short_description = _("Price")

    def trend_indicator(self, obj):
        previous = getattr(obj, 'previous_price', None)
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
            value=f"{delta:,.2f}"
        )

    trend_indicator.short_description = _("Change")

    def notes_preview(self, obj):
        if not obj.notes:
            return "—"
        return (obj.notes[:60] + "…") if len(obj.notes) > 60 else obj.notes

    notes_preview.short_description = _("Notes")

    def previous_price_display(self, obj):
        previous = getattr(obj, 'previous_price', None)
        if previous is None:
            return _("No previous price.")
        delta = obj.price - previous
        return f"Previous: {previous:,.2f} · Δ {delta:+,.2f}"

    previous_price_display.short_description = _("Previous price")

    def preview_with_template(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, _("Select at least one record."), level=messages.WARNING)
            return None
        type_ids = queryset.values_list('special_price_type_id', flat=True).distinct()
        if type_ids.count() > 1:
            self.message_user(
                request,
                _("Select records for a single special price type."),
                level=messages.WARNING,
            )
            return None
        special_type_id = type_ids.first()
        template = Template.objects.filter(special_price_type_id=special_type_id).order_by('-updated_at').first()
        if not template:
            self.message_user(
                request,
                _("No template is linked to this special price type."),
                level=messages.WARNING,
            )
            return None

        payload = self._build_payload(template, queryset.first())
        image = render_template(template, payload)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="image/png")
        response["Content-Disposition"] = 'attachment; filename="special-price-preview.png"'
        return response

    preview_with_template.short_description = _("Preview template with selected price")

    def _build_payload(self, template, price_entry):
        now = timezone.localtime()
        payload = {
            "english_date": now.strftime("%Y-%m-%d %H:%M"),
            "persian_date": now.strftime("%Y/%m/%d"),
        }
        fields = (template.config or {}).get("fields", {})
        for field_name in fields.keys():
            lower = field_name.lower()
            if "price" in lower:
                payload[field_name] = self._format_price(price_entry)
            elif "name" in lower:
                payload[field_name] = price_entry.special_price_type.name
            else:
                payload.setdefault(field_name, field_name.replace("_", " ").title())
        return payload

    def _format_price(self, entry: SpecialPriceHistory) -> str:
        value = entry.price
        if isinstance(value, Decimal):
            value = f"{value:,.2f}"
        pair = f"{entry.special_price_type.source_currency.code}/{entry.special_price_type.target_currency.code}"
        return f"{value} {pair}"
