from django.contrib import admin
from .models import Finalization, FinalizedPriceHistory, SpecialPriceFinalization


@admin.register(Finalization)
class FinalizationAdmin(admin.ModelAdmin):
    list_display = ('category', 'channel', 'finalized_at', 'finalized_by', 'message_sent')
    list_filter = ('category', 'channel', 'message_sent', 'finalized_at')
    search_fields = ('category__name', 'notes', 'image_caption', 'telegram_response')
    readonly_fields = ('finalized_at',)
    date_hierarchy = 'finalized_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'channel', 'finalized_by', 'finalized_at')
        }),
        ('Telegram', {
            'fields': ('message_sent', 'image_caption', 'telegram_response')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(FinalizedPriceHistory)
class FinalizedPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('finalization', 'price_history', 'get_category', 'get_price_type')
    list_filter = ('finalization__category', 'finalization__finalized_at')
    search_fields = ('finalization__category__name', 'price_history__price_type__name')
    
    def get_category(self, obj):
        return obj.finalization.category.name
    get_category.short_description = 'Category'
    get_category.admin_order_field = 'finalization__category'
    
    def get_price_type(self, obj):
        return obj.price_history.price_type.name
    get_price_type.short_description = 'Price Type'
    get_price_type.admin_order_field = 'price_history__price_type'


@admin.register(SpecialPriceFinalization)
class SpecialPriceFinalizationAdmin(admin.ModelAdmin):
    list_display = ('get_special_price_type', 'channel', 'finalized_at', 'finalized_by', 'message_sent')
    list_filter = ('channel', 'message_sent', 'finalized_at')
    search_fields = ('special_price_history__special_price_type__name', 'notes', 'image_caption', 'telegram_response')
    readonly_fields = ('finalized_at',)
    date_hierarchy = 'finalized_at'
    
    def get_special_price_type(self, obj):
        return obj.special_price_history.special_price_type.name
    get_special_price_type.short_description = 'Special Price Type'
    get_special_price_type.admin_order_field = 'special_price_history__special_price_type'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('special_price_history', 'channel', 'finalized_by', 'finalized_at')
        }),
        ('Telegram', {
            'fields': ('message_sent', 'image_caption', 'telegram_response')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
