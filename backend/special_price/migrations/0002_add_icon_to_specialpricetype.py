# Add optional icon field for UI highlight (e.g. Gold Star, Shield)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('special_price', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='specialpricetype',
            name='icon',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
