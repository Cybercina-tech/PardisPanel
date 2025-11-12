from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finalize", "0002_specialpricefinalization"),
    ]

    operations = [
        migrations.RenameField(
            model_name="finalization",
            old_name="message_text",
            new_name="image_caption",
        ),
        migrations.RenameField(
            model_name="specialpricefinalization",
            old_name="message_text",
            new_name="image_caption",
        ),
        migrations.AddField(
            model_name="finalization",
            name="telegram_response",
            field=models.TextField(
                blank=True,
                help_text="Raw response or error message returned by Telegram.",
                null=True,
                verbose_name="Telegram Response",
            ),
        ),
        migrations.AddField(
            model_name="specialpricefinalization",
            name="telegram_response",
            field=models.TextField(
                blank=True,
                help_text="Raw response or error message returned by Telegram.",
                null=True,
                verbose_name="Telegram Response",
            ),
        ),
    ]

