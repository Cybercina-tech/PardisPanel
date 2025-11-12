from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("telegram_app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DefaultMessageSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("default_caption", models.TextField(blank=True, help_text="Optional caption appended to generated messages.", verbose_name="Default Caption")),
                ("default_buttons", models.JSONField(blank=True, default=list, help_text='JSON structure describing inline buttons. Example: [[{"text": "View", "url": "https://example.com"}]]', verbose_name="Default Buttons")),
                ("active", models.BooleanField(default=True, help_text="Only one setting can be active per bot.", verbose_name="Active")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated At")),
                ("bot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="message_settings", to="telegram_app.telegrambot", verbose_name="Bot")),
            ],
            options={
                "verbose_name": "Default Message Setting",
                "verbose_name_plural": "Default Message Settings",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="defaultmessagesettings",
            constraint=models.UniqueConstraint(condition=models.Q(("active", True)), fields=("bot",), name="unique_active_message_settings_per_bot"),
        ),
    ]

