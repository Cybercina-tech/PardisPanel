from django.db import migrations


def ensure_pound_cash_buy_pricetype(apps, schema_editor):
    Category = apps.get_model("category", "Category")
    Currency = apps.get_model("category", "Currency")
    PriceType = apps.get_model("category", "PriceType")

    pound_category = (
        Category.objects.filter(name__iregex=r"(پوند|pound|gbp)").order_by("id").first()
    )
    if not pound_category:
        return

    gbp = Currency.objects.filter(code__iexact="GBP").first()
    irt = Currency.objects.filter(code__iexact="IRT").first()
    if not gbp or not irt:
        return

    PriceType.objects.get_or_create(
        category=pound_category,
        name="خرید نقدی",
        defaults={
            "trade_type": "buy",
            "source_currency": gbp,
            "target_currency": irt,
            "description": "خرید پوند نقدی",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0005_create_default_currencies"),
    ]

    operations = [
        migrations.RunPython(
            ensure_pound_cash_buy_pricetype,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

