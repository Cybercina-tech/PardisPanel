# Generated manually for SmartExchange Panel Phase 1

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('setting', '0003_sitesettings_alter_log_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='office_map_url',
            field=models.URLField(
                blank=True,
                help_text='Google Maps or similar URL for office location (used in Telegram captions)',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='business_hours',
            field=models.TextField(
                blank=True,
                default='دوشنبه تا شنبه: 9:30 صبح تا ۱۷\nیکشنبه ها: تعطیل',
                help_text='Business hours text (Persian/English) for Telegram captions',
            ),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='support_phone_2',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='support_phone_3',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
