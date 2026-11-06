from django.db import migrations, models

LEGACY_NAMES = ("SmartExchange", "Mr Exchange")


def forwards_rename_site(apps, schema_editor):
    SiteSettings = apps.get_model("setting", "SiteSettings")
    for row in SiteSettings.objects.filter(site_name__in=LEGACY_NAMES):
        row.site_name = "MrExchange"
        row.save(update_fields=["site_name"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("setting", "0012_telegram_webhook_base_url"),
    ]

    operations = [
        migrations.RunPython(forwards_rename_site, noop_reverse),
        migrations.AlterField(
            model_name="sitesettings",
            name="site_name",
            field=models.CharField(default="MrExchange", max_length=100),
        ),
    ]
