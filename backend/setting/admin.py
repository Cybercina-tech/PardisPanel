from django.contrib import admin
from .models import PriceThemeState, Log, SiteSettings


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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_name', 'tagline', 'support_phone', 'support_email')
    fieldsets = (
        ('Branding', {
            'fields': ('site_name', 'tagline', 'logo', 'favicon'),
            'description': 'Logo and favicon appear in the navbar and browser tab.',
        }),
        ('Contact (used in footer and Telegram captions)', {
            'fields': ('support_phone', 'support_phone_2', 'support_phone_3', 'support_email'),
        }),
        ('Office & Business', {
            'fields': ('address', 'office_map_url', 'business_hours'),
            'description': 'Office address and map URL are used in Telegram price post captions.',
        }),
        ('Social Links', {
            'fields': ('telegram_link', 'instagram_link', 'twitter_link', 'linkedin_link'),
        }),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
