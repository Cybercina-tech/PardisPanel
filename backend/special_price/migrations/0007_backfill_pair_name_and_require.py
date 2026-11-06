from django.db import migrations, models


def backfill_pair_names(apps, schema_editor):
    SpecialPricePair = apps.get_model("special_price", "SpecialPricePair")

    for pair in SpecialPricePair.objects.select_related(
        "special_price_type", "source_currency", "target_currency"
    ).all().iterator():
        if pair.name:
            continue
        trade = "Buy" if pair.trade_type == "buy" else "Sell"
        pair.name = (
            f"{pair.special_price_type.name} - "
            f"{trade} {pair.source_currency.code}/{pair.target_currency.code}"
        )[:150]
        pair.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("special_price", "0006_specialpricepair_name"),
    ]

    operations = [
        migrations.RunPython(backfill_pair_names, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="specialpricepair",
            name="name",
            field=models.CharField(max_length=150),
        ),
    ]
