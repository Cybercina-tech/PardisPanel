from django import forms
from django.contrib import admin
from django.contrib import messages
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import DefaultMessageSettings, TelegramBot, TelegramChannel
from .services.telegram_client import TelegramService


@admin.register(TelegramBot)
class TelegramBotAdmin(admin.ModelAdmin):
    """Admin interface for TelegramBot model."""
    
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'token')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'token', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make token readonly if object exists to prevent accidental changes."""
        if obj:
            return self.readonly_fields + ('token',)
        return self.readonly_fields


@admin.register(TelegramChannel)
class TelegramChannelAdmin(admin.ModelAdmin):
    """Admin interface for TelegramChannel model."""
    
    list_display = ('name', 'bot', 'chat_id', 'is_active', 'created_at')
    list_filter = ('bot', 'is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'bot__name', 'chat_id')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('bot',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'bot', 'chat_id', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )       


@admin.register(DefaultMessageSettings)
class DefaultMessageSettingsAdmin(admin.ModelAdmin):
    list_display = ("bot", "active", "updated_at")
    list_filter = ("active", "updated_at", "bot")
    search_fields = ("bot__name",)
    readonly_fields = ("created_at", "updated_at", "preview_markup")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "bot",
                    "active",
                    "default_caption",
                    "default_buttons",
                    "preview_markup",
                )
            },
        ),
        (
            _("Metadata"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    actions = ("preview_in_chat",)

    formfield_overrides = {
        models.JSONField: {
            "widget": forms.Textarea(
                attrs={
                    "rows": 6,
                    "class": "vLargeTextField monospace",
                    "placeholder": '[ [{"text": "View", "url": "https://example.com"}] ]',
                }
            )
        }
    }

    @admin.display(description=_("Preview"))
    def preview_markup(self, obj):
        if not obj:
            return _("Save to preview.")
        buttons = obj.default_buttons or []
        if not buttons:
            return _("No buttons configured.")
        markup = "<br>".join(
            " | ".join(f"{btn.get('text')} → {btn.get('url') or btn.get('callback_data')}" for btn in row)
            for row in buttons
        )
        return mark_safe(markup)

    @admin.action(description=_("Send preview to first active channel"))
    def preview_in_chat(self, request, queryset):
        for setting in queryset:
            channel = setting.bot.channels.filter(is_active=True).first()
            if not channel:
                self.message_user(
                    request,
                    _(f"No active channels for bot '{setting.bot}'."),
                    level=messages.WARNING,
                )
                continue

            try:
                client = TelegramService(setting.bot.token)
                success, detail = client.send_message(
                    chat_id=channel.chat_id,
                    text=setting.default_caption or "Preview caption",
                    buttons=setting.default_buttons,
                )
            except Exception as exc:  # pragma: no cover
                success = False
                detail = str(exc)

            if success:
                self.message_user(
                    request,
                    _(f"Preview sent to {channel.chat_id}: {detail}"),
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    _(f"Failed to send preview to {channel.chat_id}: {detail}"),
                    level=messages.ERROR,
                )