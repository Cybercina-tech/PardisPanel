from django.db import migrations


def normalize_pound_category_rates(apps, schema_editor):
    Category = apps.get_model("category", "Category")
    Currency = apps.get_model("category", "Currency")
    PriceType = apps.get_model("category", "PriceType")

    pound_category = (
        Category.objects.filter(name__iregex=r"(پوند|pound|gbp)").order_by("id").first()
    )
    if not pound_category:
        return

    tether_category = (
        Category.objects.filter(name__iregex=r"(تتر|tether|usdt)").order_by("id").first()
    )

    # Remove/move tether<->rial rows from pound category.
    pound_rows = PriceType.objects.select_related(
        "source_currency", "target_currency"
    ).filter(category=pound_category)
    for pt in pound_rows:
        source = (getattr(pt.source_currency, "code", "") or "").upper()
        target = (getattr(pt.target_currency, "code", "") or "").upper()
        name = (pt.name or "").lower()

        is_tether_irr_pair = {"USDT", "IRT"} <= {source, target} or {"USDT", "IRR"} <= {source, target}
        name_says_tether_rial = (
            any(token in name for token in ("تتر", "tether", "usdt"))
            and any(token in name for token in ("ریال", "rial", "تومان", "تومن", "irr", "irt"))
        )
        if not (is_tether_irr_pair or name_says_tether_rial):
            continue

        if tether_category:
            pt.category = tether_category
            pt.save(update_fields=["category"])
        else:
            pt.delete()

    # Ensure lira exists under pound category.
    try_currency = Currency.objects.filter(code__iexact="TRY").first()
    irt = Currency.objects.filter(code__iexact="IRT").first() or Currency.objects.filter(
        code__iexact="IRR"
    ).first()
    if try_currency and irt:
        PriceType.objects.get_or_create(
            category=pound_category,
            name="لیر",
            defaults={
                "trade_type": "buy",
                "source_currency": try_currency,
                "target_currency": irt,
                "description": "نرخ لیر در کتگوری پوند",
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("category", "0006_ensure_pound_cash_buy_pricetype"),
    ]

    operations = [
        migrations.RunPython(
            normalize_pound_category_rates,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

