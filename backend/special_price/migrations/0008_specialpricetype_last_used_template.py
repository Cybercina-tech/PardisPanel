from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("special_price", "0007_backfill_pair_name_and_require"),
        ("template_editor", "0007_template_publish_telegram_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialpricetype",
            name="last_used_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Last template used for Telegram finalize (round-robin among active templates).",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="template_editor.template",
            ),
        ),
    ]
