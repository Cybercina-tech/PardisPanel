# Generated manually on 2025-11-03

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('change_price', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pricehistory',
            name='buy_price',
        ),
        migrations.RemoveField(
            model_name='pricehistory',
            name='sell_price',
        ),
        migrations.AddField(
            model_name='pricehistory',
            name='price',
            field=models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=False,
        ),
    ]

