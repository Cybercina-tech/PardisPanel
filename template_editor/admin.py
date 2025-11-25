import copy
import io
import json
import os
import zipfile
from hashlib import md5

from django.contrib import admin, messages
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .admin_forms import TemplateAdminForm, TemplateConfigImportForm
from .models import Template
from .utils import render_template

PREVIEW_CACHE_PREFIX = "admin-template-preview"
BADGE_BASE_STYLE = (
    "display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;"
    "text-transform:uppercase;letter-spacing:0.05em;"
)


def _serialize_config(config: dict) -> str:
    return json.dumps(config or {"fields": {}}, indent=2, ensure_ascii=False)


def _build_preview_payload(template: Template) -> dict:
    now = timezone.localtime()
    base_payload = {
        "english_date": now.strftime("%Y-%m-%d %H:%M"),
        "timestamp": now.isoformat(timespec="minutes"),
        "persian_date": now.strftime("%Y/%m/%d"),
        "category_name": template.category.name if template.category else template.name,
    }
    fields = (template.config or {}).get("fields", {})
    for field_name, field in fields.items():
        if field_name in base_payload:
            continue
        sample = field.get("sample_text") or field_name.replace("_", " ").title()
        base_payload[field_name] = sample
    return base_payload


def _merge_config(existing: dict, incoming: dict) -> dict:
    merged = copy.deepcopy(existing) if existing else {"fields": {}}
    merged_fields = merged.setdefault("fields", {})
    for key, value in (incoming or {}).get("fields", {}).items():
        merged_fields[key] = value
    return merged


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    form = TemplateAdminForm
    list_display = (
        "thumbnail_tag",
        "name",
        "assignment_target",
        "field_count",
        "updated_at",
        "preview_link",
    )
    list_display_links = ("thumbnail_tag", "name")
    list_filter = ("category", "special_price_type", "created_at", "updated_at")
    search_fields = ("name", "category__name", "special_price_type__name")
    readonly_fields = ("created_at", "updated_at", "rendered_config", "live_preview", "field_overview")
    ordering = ("-updated_at",)
    autocomplete_fields = ("category", "special_price_type")
    list_per_page = 25
    actions = ("duplicate_templates", "export_template_config", "import_template_config_action")

    fieldsets = (
        (_("Template"), {"fields": ("name", "image", "live_preview")}),
        (
            _("Assignment"),
            {
                "fields": ("category", "special_price_type"),
                "description": _("Link the template to either a category or a special price type."),
            },
        ),
        (
            _("Configuration"),
            {
                "fields": ("config", "field_overview", "rendered_config"),
                "classes": ("wide",),
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category", "special_price_type")

    # ------------------------------------------------------------------
    # List & detail helpers
    # ------------------------------------------------------------------
    def thumbnail_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" alt="{}" class="admin-template-thumb"/>',
                obj.image.url,
                obj.name,
            )
        return _("No image")

    thumbnail_tag.short_description = _("Preview")

    def assignment_target(self, obj):
        if obj.category:
            return format_html(
                '<span style="{}background:#e8f5e9;color:#2e7d32;">{}</span>',
                BADGE_BASE_STYLE,
                obj.category.name,
            )
        if obj.special_price_type:
            return format_html(
                '<span style="{}background:#f3e5f5;color:#6a1b9a;">{}</span>',
                BADGE_BASE_STYLE,
                obj.special_price_type.name,
            )
        return _("Unassigned")

    assignment_target.short_description = _("Target")

    def field_count(self, obj):
        return len((obj.config or {}).get("fields", {}))

    field_count.short_description = _("Fields")

    def preview_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("admin:template_editor_template_preview", args=[obj.pk])
        return format_html('<a href="{}" class="button" target="_blank">Open preview</a>', url)

    preview_link.short_description = _("Live preview")

    def rendered_config(self, obj):
        if not obj.config:
            return _("No configuration")
        return mark_safe(f"<pre>{_serialize_config(obj.config)}</pre>")

    rendered_config.short_description = _("Serialized JSON")

    def field_overview(self, obj):
        fields = (obj.config or {}).get("fields", {})
        if not fields:
            return _("No text fields configured.")

        rows = []
        for name, data in list(fields.items())[:12]:
            rows.append(
                "<tr>"
                f"<td><code>{name}</code></td>"
                f"<td>{data.get('x', 0)}</td>"
                f"<td>{data.get('y', 0)}</td>"
                f"<td>{data.get('size', 0)}</td>"
                f"<td>{data.get('align', 'left')}</td>"
                "</tr>"
            )
        html = (
            "<table class='field-overview-table'>"
            "<thead><tr><th>Field</th><th>X</th><th>Y</th><th>Size</th><th>Align</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )
        if len(fields) > 12:
            html += f"<p>… +{len(fields) - 12} more</p>"
        return mark_safe(html)

    field_overview.short_description = _("Field overview")

    def live_preview(self, obj):
        if not obj.pk:
            return _("Save the template first to enable preview.")
        if not obj.image:
            return _("Upload an image to generate previews.")
        url = reverse("admin:template_editor_template_preview", args=[obj.pk])
        return format_html(
            '<div class="template-preview js-template-preview" data-preview-url="{}">'
            '<div class="template-preview__actions">'
            '<button type="button" class="button js-refresh-preview">Refresh preview</button>'
            '<a href="{}" target="_blank" class="button button-small">Open in new tab</a>'
            "</div>"
            '<img src="{}?t={}" alt="Template preview" class="template-preview__image"/>'
            "</div>",
            url,
            url,
            url,
            timezone.now().timestamp(),
        )

    live_preview.short_description = _("Live preview")

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        warnings = getattr(form, "config_warnings", [])
        for warning in warnings:
            messages.warning(request, warning)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def duplicate_templates(self, request, queryset):
        created = 0
        for template in queryset:
            new_name = self._generate_copy_name(template.name)
            duplicate = Template(
                name=new_name,
                category=template.category,
                special_price_type=template.special_price_type,
                config=copy.deepcopy(template.config),
            )
            if template.image:
                template.image.open("rb")
                try:
                    duplicate.image.save(
                        self._build_duplicate_filename(template),
                        ContentFile(template.image.read()),
                        save=False,
                    )
                finally:
                    template.image.close()
            duplicate.save()
            created += 1
        self.message_user(request, _(f"Successfully duplicated {created} template(s)."), messages.SUCCESS)

    duplicate_templates.short_description = _("Duplicate selected templates")

    def export_template_config(self, request, queryset):
        count = queryset.count()
        if not count:
            self.message_user(request, _("Select at least one template to export."), level=messages.WARNING)
            return None

        if count == 1:
            template = queryset.first()
            content = _serialize_config(template.config)
            response = HttpResponse(content, content_type="application/json")
            filename = f"{slugify(template.name) or 'template'}.json"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for template in queryset:
                filename = f"{slugify(template.name) or 'template'}_{template.pk}.json"
                archive.writestr(filename, _serialize_config(template.config))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="template-configs.zip"'
        return response

    export_template_config.short_description = _("Export template config (JSON/zip)")

    def import_template_config_action(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, _("Please select at least one template to import into."), messages.WARNING)
            return None
        selected = ",".join(str(pk) for pk in queryset.values_list("pk", flat=True))
        url = reverse("admin:template_editor_template_import_config")
        return HttpResponseRedirect(f"{url}?ids={selected}")

    import_template_config_action.short_description = _("Import template config…")

    # ------------------------------------------------------------------
    # Custom admin views
    # ------------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="template_editor_template_preview",
            ),
            path(
                "import-config/",
                self.admin_site.admin_view(self.import_config_view),
                name="template_editor_template_import_config",
            ),
        ]
        return custom_urls + urls

    def preview_view(self, request, object_id):
        template = get_object_or_404(Template, pk=object_id)
        if not template.image:
            raise Http404("Template has no image.")

        config_payload = template.config
        posted_config = request.POST.get("config")
        if posted_config:
            try:
                config_payload = json.loads(posted_config)
            except json.JSONDecodeError:
                pass

        temp_template = copy.copy(template)
        temp_template.config = config_payload

        cache_key = self._preview_cache_key(
            template.pk,
            config_payload,
            template.image.name,
            template.updated_at,
        )
        cached = cache.get(cache_key)
        if cached:
            return HttpResponse(cached, content_type="image/png")

        image = render_template(temp_template, _build_preview_payload(temp_template))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        content = buffer.getvalue()
        cache.set(cache_key, content, timeout=120)
        return HttpResponse(content, content_type="image/png")

    def import_config_view(self, request):
        ids_param = request.GET.get("ids") or request.POST.get("ids")
        if not ids_param:
            self.message_user(request, _("No templates were selected for import."), messages.ERROR)
            return HttpResponseRedirect(
                reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist")
            )

        selected_ids = [int(pk) for pk in ids_param.split(",") if pk]
        templates = Template.objects.filter(pk__in=selected_ids)
        if not templates.exists():
            self.message_user(request, _("Selected templates no longer exist."), messages.ERROR)
            return HttpResponseRedirect(
                reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist")
            )

        if request.method == "POST":
            form = TemplateConfigImportForm(request.POST, request.FILES)
            if form.is_valid() and form.parsed_config:
                merge_strategy = form.cleaned_data["merge_strategy"]
                dry_run = form.cleaned_data["dry_run"]

                for template in templates:
                    new_config = (
                        form.parsed_config if merge_strategy == "replace" else _merge_config(template.config, form.parsed_config)
                    )
                    if not dry_run:
                        template.config = new_config
                        template.save(update_fields=["config", "updated_at"])

                level = messages.WARNING if dry_run else messages.SUCCESS
                action = "validated" if dry_run else "updated"
                self.message_user(
                    request,
                    _(f"{templates.count()} template(s) {action} successfully."),
                    level=level,
                )
                for warning in form.config_warnings:
                    messages.warning(request, warning)

                if dry_run:
                    return HttpResponseRedirect(request.path + f"?ids={ids_param}")
                return HttpResponseRedirect(
                    reverse(f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist")
                )
        else:
            form = TemplateConfigImportForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "selected_templates": templates,
            "ids": ids_param,
            "title": _("Import configuration"),
        }
        return render(request, "template_editor/admin/import_config.html", context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _generate_copy_name(self, base_name: str) -> str:
        suffix = 1
        candidate = f"{base_name} (copy)"
        while Template.objects.filter(name=candidate).exists():
            suffix += 1
            candidate = f"{base_name} (copy {suffix})"
        return candidate

    def _build_duplicate_filename(self, template: Template) -> str:
        base, ext = os.path.splitext(os.path.basename(template.image.name))
        cleaned = slugify(base) or "template"
        return f"templates/{cleaned}-copy{ext or '.png'}"

    def _preview_cache_key(self, pk: int, config: dict, image_name: str, updated_at) -> str:
        serialized = json.dumps(config or {}, sort_keys=True)
        digest = md5(serialized.encode("utf-8")).hexdigest()
        stamp = int(updated_at.timestamp()) if updated_at else 0
        return f"{PREVIEW_CACHE_PREFIX}:{pk}:{digest}:{image_name}:{stamp}"

