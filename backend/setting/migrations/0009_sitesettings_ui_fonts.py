# Generated manually for UI font preferences

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("setting", "0008_sitesettings_upload_policy_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="ui_font_filename_ltr",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional .ttf/.otf filename under static/fonts for LTR UI. Empty = default stack.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="ui_font_filename_rtl",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Optional .ttf/.otf filename under static/fonts for RTL UI (Persian). Empty = default stack.",
                max_length=255,
            ),
        ),
    ]
