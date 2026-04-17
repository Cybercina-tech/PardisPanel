from django.db import migrations


def ensure_tether_euro_pricetype(apps, schema_editor):
    Category = apps.get_model("category", "Category")
    Currency = apps.get_model("category", "Currency")
    PriceType = apps.get_model("category", "PriceType")

    tether_category = (
        Category.objects.filter(name__iregex=r"(تتر|tether|usdt)").order_by("id").first()
    )
    if not tether_category:
        return

    eur = Currency.objects.filter(code__iexact="EUR").first()
    irt = Currency.objects.filter(code__iexact="IRT").first() or Currency.objects.filter(
        code__iexact="IRR"
    ).first()
    if not eur or not irt:
        return

    PriceType.objects.get_or_create(
        category=tether_category,
        name="یورو",
        defaults={
            "trade_type": "buy",
            "source_currency": eur,
            "target_currency": irt,
            "description": "نرخ یورو در بنر تتر",
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0007_move_tether_irr_out_of_pound_add_lira"),
    ]

    operations = [
        migrations.RunPython(
            ensure_tether_euro_pricetype,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

