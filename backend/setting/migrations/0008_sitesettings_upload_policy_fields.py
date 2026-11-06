from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("setting", "0007_sitesettings_base_currency_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="upload_allowed_formats",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Allowed upload formats list, e.g. ['PNG', 'JPG', 'SVG'].",
            ),
        ),
        migrations.AddField(
            model_name="sitesettings",
            name="upload_max_file_size_mb",
            field=models.PositiveIntegerField(
                default=5,
                help_text="Maximum upload size in MB for managed uploads.",
            ),
        ),
    ]
