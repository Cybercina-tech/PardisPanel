import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0007_template_publish_telegram_fields"),
        ("category", "0009_alter_category_inline_buttons"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="last_used_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Last template_editor.Template used for round-robin price image publishing.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="template_editor.template",
            ),
        ),
    ]
