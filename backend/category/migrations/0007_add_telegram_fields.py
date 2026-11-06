# Telegram message fields for Category (Telegram Message Studio)

from django.db import migrations, models


def default_inline_buttons():
    return []


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0006_add_is_active_and_order_to_pricetype'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='telegram_message_description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='category',
            name='telegram_media_url',
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='category',
            name='inline_buttons',
            field=models.JSONField(blank=True, default=default_inline_buttons),
        ),
    ]
