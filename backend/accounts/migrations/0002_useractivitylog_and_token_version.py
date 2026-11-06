# User activity log and token_version for force logout

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='token_version',
            field=models.PositiveIntegerField(default=0, help_text='Incremented on force logout to invalidate all tokens.'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('management', 'Management'),
                    ('employee', 'Employee'),
                    ('developer', 'Developer'),
                ],
                default='employee',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='UserActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('login_success', 'Login success'), ('login_failed', 'Login failed'), ('logout', 'Logout'), ('price_update', 'Price update'), ('bulk_price_update', 'Bulk price update'), ('special_price_update', 'Special price update'), ('template_change', 'Template change'), ('finalize', 'Finalize'), ('other', 'Other')], max_length=32)),
                ('ip_address', models.CharField(blank=True, max_length=45)),
                ('user_agent', models.TextField(blank=True)),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activity_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User activity log',
                'verbose_name_plural': 'User activity logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='useractivitylog',
            index=models.Index(fields=['-created_at'], name='accounts_us_created_idx'),
        ),
        migrations.AddIndex(
            model_name='useractivitylog',
            index=models.Index(fields=['action_type', '-created_at'], name='accounts_us_action_idx'),
        ),
        migrations.AddIndex(
            model_name='useractivitylog',
            index=models.Index(fields=['user', '-created_at'], name='accounts_us_user_idx'),
        ),
    ]
