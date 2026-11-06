# Add unique constraint (category, source_currency, target_currency, trade_type)
# and remove any existing duplicates by keeping the row with smallest id per group.

from django.db import migrations, models


def remove_duplicate_currency_pair_trade(apps, schema_editor):
    """Keep one PriceType per (category, source_currency, target_currency, trade_type); delete the rest."""
    PriceType = apps.get_model("category", "PriceType")
    from django.db.models import Count
    duplicates = (
        PriceType.objects.values("category", "source_currency", "target_currency", "trade_type")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )
    for row in duplicates:
        keep_ids = list(
            PriceType.objects.filter(
                category_id=row["category"],
                source_currency_id=row["source_currency"],
                target_currency_id=row["target_currency"],
                trade_type=row["trade_type"],
            )
            .order_by("id")
            .values_list("id", flat=True)
        )
        if len(keep_ids) <= 1:
            continue
        ids_to_delete = keep_ids[1:]
        PriceType.objects.filter(id__in=ids_to_delete).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("category", "0007_add_telegram_fields"),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_currency_pair_trade, noop),
        migrations.AddConstraint(
            model_name="pricetype",
            constraint=models.UniqueConstraint(
                fields=("category", "source_currency", "target_currency", "trade_type"),
                name="unique_category_currency_pair_trade",
            ),
        ),
    ]
