from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("template_editor", "0005_pixelcast_config_json_layer_widget"),
    ]

    operations = [
        migrations.AlterField(
            model_name="template",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Background image for the template (optional; editor can use solid color only)",
                null=True,
                upload_to="templates/",
            ),
        ),
    ]
