from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("category", "0011_repair_last_used_template_column"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pricetype",
            name="unique_category_currency_pair_trade",
        ),
    ]

