from django.contrib import admin
from .models import SpecialPriceType, SpecialPriceHistory


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
    list_display = ('special_price_type', 'price', 'created_at', 'updated_at')
    list_filter = ('special_price_type', 'created_at')
    search_fields = ('special_price_type__name', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Price Information', {
            'fields': ('special_price_type', 'price', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
