from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0006_template_image_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="If false, excluded from round-robin publishing for this category/special.",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="publish_order",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Lower values are used first in round-robin order within the same category.",
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="telegram_caption_template",
            field=models.TextField(
                blank=True,
                help_text=(
                    "Optional HTML caption for Telegram when this template is used. "
                    "Placeholders: {date_fa}, {pair_name}, {price__slug}, etc. from dynamic data."
                ),
            ),
        ),
        migrations.AddField(
            model_name="template",
            name="telegram_buttons_json",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Inline keyboard rows, e.g. [[{"text": "…", "url": "https://…"}]].',
            ),
        ),
    ]
