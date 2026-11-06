# Generated for template-based price banners migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setting', '0004_add_office_and_contact_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='use_template_editor_for_boards',
            field=models.BooleanField(
                default=False,
                help_text='If enabled, category/tether/special price boards use template_editor Template and render_price_template instead of legacy renderers.',
            ),
        ),
    ]
