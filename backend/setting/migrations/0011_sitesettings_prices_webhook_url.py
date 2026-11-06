from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("setting", "0010_sitesettings_site_name_mr_exchange"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="prices_webhook_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="If set, the panel POSTs a JSON prices snapshot to this URL after each price update.",
                max_length=500,
            ),
        ),
    ]
