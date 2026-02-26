# Data migration: seed double-price types "قیمت خرید ویژه نقدی و حسابی" and "قیمت فروش ویژه نقدی و حسابی".
# Uses RunPython so that on every deploy (including fresh DB) these types exist.
# Lookup by slug so that name can be updated to Persian without breaking idempotency.

from django.db import migrations


def seed_double_price_types(apps, schema_editor):
    Currency = apps.get_model("category", "Currency")
    SpecialPriceType = apps.get_model("special_price", "SpecialPriceType")

    gbp, _ = Currency.objects.get_or_create(
        code="GBP",
        defaults={"name": "British Pound", "symbol": "£"},
    )
    irr, _ = Currency.objects.get_or_create(
        code="IRR",
        defaults={"name": "Iranian Rial", "symbol": "﷼"},
    )

    SpecialPriceType.objects.update_or_create(
        slug="special-gbp-buy",
        defaults={
            "name": "قیمت خرید ویژه نقدی و حسابی",
            "description": "",
            "source_currency_id": gbp.pk,
            "target_currency_id": irr.pk,
            "trade_type": "buy",
            "is_double_price": True,
        },
    )
    SpecialPriceType.objects.update_or_create(
        slug="special-gbp-sell",
        defaults={
            "name": "قیمت فروش ویژه نقدی و حسابی",
            "description": "",
            "source_currency_id": gbp.pk,
            "target_currency_id": irr.pk,
            "trade_type": "sell",
            "is_double_price": True,
        },
    )


def reverse_seed(apps, schema_editor):
    SpecialPriceType = apps.get_model("special_price", "SpecialPriceType")
    SpecialPriceType.objects.filter(
        slug__in=("special-gbp-buy", "special-gbp-sell"),
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("special_price", "0002_double_price_fields"),
        ("category", "0004_remove_pricetype_unique_category_pair_trade"),
    ]

    operations = [
        migrations.RunPython(seed_double_price_types, reverse_seed),
    ]
