from django.db import migrations, models


def create_default_currency(apps, schema_editor):
    Currency = apps.get_model('category', 'Currency')
    PriceType = apps.get_model('category', 'PriceType')
    # Create or get a default currency (USD)
    currency, created = Currency.objects.get_or_create(code='USD', defaults={'name': 'US Dollar', 'symbol': '$'})
    # Backfill existing PriceType rows
    PriceType.objects.filter(source_currency__isnull=True).update(source_currency=currency)
    PriceType.objects.filter(target_currency__isnull=True).update(target_currency=currency)
    PriceType.objects.filter(trade_type__isnull=True).update(trade_type='buy')


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0002_currency_alter_pricetype_unique_together_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_currency, reverse_code=migrations.RunPython.noop),
        # Alter fields to be non-nullable
        migrations.AlterField(
            model_name='pricetype',
            name='source_currency',
            field=models.ForeignKey(on_delete=models.PROTECT, related_name='+', to='category.currency'),
        ),
        migrations.AlterField(
            model_name='pricetype',
            name='target_currency',
            field=models.ForeignKey(on_delete=models.PROTECT, related_name='+', to='category.currency'),
        ),
        migrations.AlterField(
            model_name='pricetype',
            name='trade_type',
            field=models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=10),
        ),
    ]
