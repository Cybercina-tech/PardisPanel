from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("telegram_app", "0002_defaultmessagesettings"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegrambot",
            name="display_name",
            field=models.CharField(
                blank=True,
                help_text="Optional friendly display name",
                max_length=100,
                verbose_name="Display Name",
            ),
        ),
        migrations.AddField(
            model_name="telegrambot",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Optional security or usage notes",
                verbose_name="Notes",
            ),
        ),
        migrations.AddField(
            model_name="telegrambot",
            name="restrict_to_known_channels",
            field=models.BooleanField(
                default=False,
                help_text="If set, only allow sending to channels registered in this panel",
                verbose_name="Restrict to known channels",
            ),
        ),
        migrations.AddField(
            model_name="telegrambot",
            name="log_all_messages",
            field=models.BooleanField(
                default=False,
                help_text="If set, log all messages sent via this bot",
                verbose_name="Log all messages",
            ),
        ),
    ]
