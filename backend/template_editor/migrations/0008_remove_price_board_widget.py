from django.db import migrations, models


def remove_price_board_from_templates_and_widgets(apps, schema_editor):
    Template = apps.get_model("template_editor", "Template")
    Widget = apps.get_model("template_editor", "Widget")
    for tpl in Template.objects.iterator():
        raw = tpl.config_json
        if not isinstance(raw, dict):
            continue
        widgets = raw.get("widgets")
        if not isinstance(widgets, list):
            continue
        filtered = [
            w
            for w in widgets
            if isinstance(w, dict) and str(w.get("type") or "").strip() != "price_board"
        ]
        if len(filtered) == len(widgets):
            continue
        tpl.config_json = {**raw, "widgets": filtered}
        tpl.save(update_fields=["config_json"])
    Widget.objects.filter(type="price_board").delete()


def noop_reverse(apps, schema_editor):
    pass


_WIDGET_TYPE_CHOICES = [
    ("clock", "Clock"),
    ("date", "Date"),
    ("weekday", "Weekday"),
    ("countdown", "Countdown"),
    ("text", "Text"),
    ("marquee", "Marquee"),
    ("weather", "Weather"),
    ("qr_action", "QR action"),
    ("image", "Image"),
    ("video", "Video"),
    ("album", "Album"),
    ("webview", "Webview"),
    ("chart", "Chart"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0007_template_publish_telegram_fields"),
    ]

    operations = [
        migrations.RunPython(
            remove_price_board_from_templates_and_widgets,
            noop_reverse,
        ),
        migrations.AlterField(
            model_name="widget",
            name="type",
            field=models.CharField(
                choices=_WIDGET_TYPE_CHOICES,
                default="text",
                max_length=40,
            ),
        ),
    ]
