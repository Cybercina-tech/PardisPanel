# Generated manually for Double Price System

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ("special_price", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialpricetype",
            name="is_double_price",
            field=models.BooleanField(
                default=False,
                help_text="If True, this type uses two prices (Cash and Account) on one banner.",
            ),
        ),
        migrations.AddField(
            model_name="specialpricehistory",
            name="cash_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Cash price (نقدی); used when special_price_type.is_double_price is True.",
                max_digits=20,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="specialpricehistory",
            name="account_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Account price (حسابی); used when special_price_type.is_double_price is True.",
                max_digits=20,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
