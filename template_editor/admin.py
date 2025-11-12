from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from .models import Element, Template
from .renderer import render_template
from telegram_app.services.dispatcher import broadcast_rendered_template


class ElementInline(admin.TabularInline):
    model = Element
    extra = 1
    fields = ("type", "content", "x", "y", "font_size", "color")
    classes = ("collapse",)


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
    inlines = [ElementInline]
    actions = ("render_templates",)

    fieldsets = (
        ("Template Details", {"fields": ("name", "background")}),
        (
            "Metadata",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description=_("Render selected templates"))
    def render_templates(self, request, queryset):
        for template in queryset:
            try:
                render_result = render_template(template)
                dispatch_report = broadcast_rendered_template(
                    template=template,
                    image_path=render_result["path"],
                    image_url=render_result["url"],
                )
            except Exception as exc:  # pragma: no cover - admin feedback
                self.message_user(
                    request,
                    _(f"Failed to render '{template}': {exc}"),
                    level=messages.ERROR,
                )
                continue

            self.message_user(
                request,
                _(
                    "Rendered '{template}' → {url}. Dispatch: {dispatch}".format(
                        template=template,
                        url=render_result["url"],
                        dispatch=", ".join(
                            f"{item.get('channel')}: {'OK' if item.get('success') else 'FAILED'}"
                            for item in dispatch_report
                        )
                        or _("No channels configured."),
                    )
                ),
                level=messages.SUCCESS,
            )


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ("template", "type", "x", "y")
    list_filter = ("type", "template")
    search_fields = ("template__name", "content")
    list_select_related = ("template",)
    ordering = ("template__name", "id")

    fieldsets = (
        (
            "Element Details",
            {
                "fields": (
                    "template",
                    "type",
                    "content",
                    "x",
                    "y",
                    "font_size",
                    "color",
                )
            },
        ),
    )

