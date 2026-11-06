# Generated manually for Category Explorer

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0005_create_default_currencies'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricetype',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='pricetype',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='pricetype',
            options={'ordering': ['order', 'id'], 'verbose_name': 'PriceType', 'verbose_name_plural': 'PriceTypes'},
        ),
    ]
