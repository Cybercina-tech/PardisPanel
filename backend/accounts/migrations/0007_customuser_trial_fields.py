from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_customuser_owner_customuser_sub_role_and_more")]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="trial_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="trial_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="customuser",
            name="trial_expiry_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
