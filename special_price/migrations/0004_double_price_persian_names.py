# Update double-price type names to Persian (for DBs that already had 0003 applied with English names).

from django.db import migrations


def set_persian_names(apps, schema_editor):
    SpecialPriceType = apps.get_model("special_price", "SpecialPriceType")
    SpecialPriceType.objects.filter(slug="special-gbp-buy").update(
        name="قیمت خرید ویژه نقدی و حسابی",
        description="",
    )
    SpecialPriceType.objects.filter(slug="special-gbp-sell").update(
        name="قیمت فروش ویژه نقدی و حسابی",
        description="",
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("special_price", "0003_seed_double_price_types"),
    ]

    operations = [
        migrations.RunPython(set_persian_names, noop_reverse),
    ]
