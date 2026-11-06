from django.db import migrations, models


def forwards_rename_site(apps, schema_editor):
    SiteSettings = apps.get_model("setting", "SiteSettings")
    for row in SiteSettings.objects.filter(site_name="SmartExchange"):
        row.site_name = "Mr Exchange"
        row.save(update_fields=["site_name"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("setting", "0009_sitesettings_ui_fonts"),
    ]

    operations = [
        migrations.RunPython(forwards_rename_site, noop_reverse),
        migrations.AlterField(
            model_name="sitesettings",
            name="site_name",
            field=models.CharField(default="Mr Exchange", max_length=100),
        ),
    ]
