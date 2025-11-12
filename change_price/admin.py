from django.contrib import admin
from .models import PriceHistory


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('price_type', 'price', 'created_at', 'updated_at')
    list_filter = ('price_type', 'created_at')
    search_fields = ('price_type__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Price Information', {
            'fields': ('price_type', 'price', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )