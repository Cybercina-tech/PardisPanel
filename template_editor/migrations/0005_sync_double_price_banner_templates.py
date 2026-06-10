# Sync template_editor Template images for double-price GBP special types.

from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.db import migrations


def sync_double_price_banner_templates(apps, schema_editor):
    Template = apps.get_model("template_editor", "Template")
    SpecialPriceType = apps.get_model("special_price", "SpecialPriceType")

    templates_dir = Path(settings.MEDIA_ROOT) / "templates"
    banner_files = {
        "special-gbp-buy": "gbp_special_buy_banner.png",
        "special-gbp-sell": "gbp_special_sell_banner.png",
    }

    for slug, filename in banner_files.items():
        src = templates_dir / filename
        if not src.exists():
            # Legacy fallback during rollout
            legacy = {
                "gbp_special_buy_banner.png": "special_gbp_buy_double.png",
                "gbp_special_sell_banner.png": "special_gbp_sell_double.png",
            }.get(filename)
            if legacy:
                src = templates_dir / legacy
        if not src.exists():
            continue

        special_price_type = SpecialPriceType.objects.filter(slug=slug).first()
        if not special_price_type:
            continue

        template = Template.objects.filter(special_price_type_id=special_price_type.pk).first()
        if not template:
            template = Template(
                name=f"gbp-double-{slug}",
                special_price_type_id=special_price_type.pk,
            )

        with open(src, "rb") as handle:
            template.image.save(filename, File(handle), save=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0004_template_special_price_type_alter_template_category"),
        ("special_price", "0004_double_price_persian_names"),
    ]

    operations = [
        migrations.RunPython(sync_double_price_banner_templates, noop_reverse),
    ]
