from django.db import migrations, models
import django.db.models.deletion


def hard_cutover_cleanup(apps, schema_editor):
    Template = apps.get_model("template_editor", "Template")
    TemplateWidgetBinding = apps.get_model("template_editor", "TemplateWidgetBinding")

    # Hard cutover: templates without category are no longer valid.
    Template.objects.filter(category__isnull=True).delete()

    for template in Template.objects.iterator():
        raw = template.config_json if isinstance(template.config_json, dict) else {}
        widgets = raw.get("widgets")
        if not isinstance(widgets, list):
            continue
        for widget in widgets:
            if not isinstance(widget, dict):
                continue
            style = widget.get("style") if isinstance(widget.get("style"), dict) else {}
            raw_price_type_id = style.get("priceTypeId") or style.get("price_type_id")
            if raw_price_type_id in (None, ""):
                continue
            widget_id = widget.get("id")
            if not widget_id:
                continue
            try:
                ptid = int(raw_price_type_id)
            except (TypeError, ValueError):
                continue
            TemplateWidgetBinding.objects.update_or_create(
                template_id=template.id,
                widget_uuid=widget_id,
                defaults={"price_type_id": ptid},
            )


class Migration(migrations.Migration):

    dependencies = [
        ("category", "0011_repair_last_used_template_column"),
        ("template_editor", "0008_remove_price_board_widget"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateWidgetBinding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("widget_uuid", models.UUIDField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("price_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="template_bindings", to="category.pricetype")),
                ("template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="price_bindings", to="template_editor.template")),
            ],
            options={
                "ordering": ["template_id", "id"],
            },
        ),
        migrations.RemoveField(
            model_name="template",
            name="special_price_type",
        ),
        migrations.AlterField(
            model_name="template",
            name="category",
            field=models.ForeignKey(help_text="Category this template belongs to.", on_delete=django.db.models.deletion.CASCADE, to="category.category"),
        ),
        migrations.AddConstraint(
            model_name="templatewidgetbinding",
            constraint=models.UniqueConstraint(fields=("template", "widget_uuid"), name="template_widget_binding_unique_widget_per_template"),
        ),
        migrations.RunPython(hard_cutover_cleanup, migrations.RunPython.noop),
    ]
