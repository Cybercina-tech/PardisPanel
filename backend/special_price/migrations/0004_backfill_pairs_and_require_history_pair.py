from django.db import migrations, models


def backfill_pairs(apps, schema_editor):
    SpecialPriceType = apps.get_model("special_price", "SpecialPriceType")
    SpecialPricePair = apps.get_model("special_price", "SpecialPricePair")
    SpecialPriceHistory = apps.get_model("special_price", "SpecialPriceHistory")

    pair_by_type = {}
    for sp_type in SpecialPriceType.objects.all().iterator():
        pair, _ = SpecialPricePair.objects.get_or_create(
            special_price_type_id=sp_type.id,
            source_currency_id=sp_type.source_currency_id,
            target_currency_id=sp_type.target_currency_id,
        )
        pair_by_type[sp_type.id] = pair.id

    for history in SpecialPriceHistory.objects.filter(pair__isnull=True).iterator():
        pair_id = pair_by_type.get(history.special_price_type_id)
        if pair_id is not None:
            history.pair_id = pair_id
            history.save(update_fields=["pair"])


class Migration(migrations.Migration):
    dependencies = [
        ("special_price", "0003_specialpricepair_specialpricehistory_pair_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_pairs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="specialpricehistory",
            name="pair",
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name="histories",
                to="special_price.specialpricepair",
            ),
        ),
    ]
