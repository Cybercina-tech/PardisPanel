# PixelCast-style template fields and widget sync tables

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0004_template_special_price_type_alter_template_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="canvas_height",
            field=models.PositiveIntegerField(
                default=1080,
                help_text="Design canvas height in pixels (logical)",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="canvas_width",
            field=models.PositiveIntegerField(
                default=1920,
                help_text="Design canvas width in pixels (logical)",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="config_json",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="PixelCast-style layout: widgets, backgroundColor, etc.",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="orientation",
            field=models.CharField(
                choices=[("landscape", "Landscape"), ("portrait", "Portrait")],
                default="landscape",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="Layer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(default="Default Layer", max_length=120)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="editor_layers",
                        to="template_editor.template",
                    ),
                ),
            ],
            options={
                "ordering": ["template_id", "order", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="layer",
            constraint=models.UniqueConstraint(
                fields=("template", "name"),
                name="template_editor_layer_unique_name_per_template",
            ),
        ),
        migrations.CreateModel(
            name="Widget",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "widget_uuid",
                    models.UUIDField(editable=False, unique=True),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
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
                            ("price_board", "Price board"),
                        ],
                        default="text",
                        max_length=40,
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=200)),
                ("content", models.TextField(blank=True)),
                ("content_url", models.URLField(blank=True, max_length=2000)),
                ("content_json", models.JSONField(blank=True, default=dict)),
                ("x_pct", models.CharField(blank=True, max_length=32)),
                ("y_pct", models.CharField(blank=True, max_length=32)),
                ("w_pct", models.CharField(blank=True, max_length=32)),
                ("h_pct", models.CharField(blank=True, max_length=32)),
                ("z_index", models.IntegerField(default=0)),
                ("rotation", models.FloatField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "layer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="widgets",
                        to="template_editor.layer",
                    ),
                ),
            ],
            options={
                "ordering": ["layer_id", "z_index", "id"],
            },
        ),
    ]
