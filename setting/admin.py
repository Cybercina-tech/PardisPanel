from django.contrib import admin
from .models import PriceThemeState, Log


@admin.register(PriceThemeState)
class PriceThemeStateAdmin(admin.ModelAdmin):
    list_display = ('key', 'last_index', 'updated_at')
    readonly_fields = ('updated_at',)


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'level', 'source', 'message_preview', 'user')
    list_filter = ('level', 'source', 'created_at')
    search_fields = ('message', 'details')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def message_preview(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_preview.short_description = 'Message'
