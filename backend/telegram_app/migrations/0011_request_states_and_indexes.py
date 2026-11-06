from django.db import migrations, models


def remap_exchange_statuses(apps, schema_editor):
    ExchangeRequest = apps.get_model("telegram_app", "ExchangeRequest")
    ExchangeRequest.objects.filter(status__in=("pending", "notified")).update(
        status="new"
    )
    ExchangeRequest.objects.filter(status="closed").update(status="successful")


class Migration(migrations.Migration):

    dependencies = [
        ("telegram_app", "0010_admin_analytics_foundation"),
    ]

    operations = [
        migrations.RunPython(remap_exchange_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="exchangerequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("cancelled", "Canceled"),
                    ("successful", "Successful"),
                ],
                db_index=True,
                default="new",
                max_length=16,
                verbose_name="Status",
            ),
        ),
        migrations.AlterField(
            model_name="botsession",
            name="state",
            field=models.CharField(
                choices=[
                    ("START", "Start"),
                    ("MAIN_MENU", "Main Menu"),
                    ("PROFILE", "Profile"),
                    ("EXCHANGE_SOURCE", "Exchange Source"),
                    ("EXCHANGE_TARGET", "Exchange Target"),
                    ("EXCHANGE_AMOUNT", "Exchange Amount"),
                    ("EXCHANGE_PRICE", "Exchange Price"),
                    ("EXCHANGE_TTL", "Exchange TTL"),
                    ("EXCHANGE_SUMMARY", "Exchange Summary"),
                    ("ALERT_MENU", "Alert Menu"),
                    ("ALERT_SOURCE", "Alert Source"),
                    ("ALERT_TARGET", "Alert Target"),
                    ("ALERT_PRICE", "Alert Price"),
                    ("ALERT_SUMMARY", "Alert Summary"),
                    ("ADMIN_MENU", "Admin Menu"),
                    ("ADMIN_REQUEST_LIST", "Admin Request List"),
                    ("ADMIN_REQUEST_DETAIL", "Admin Request Detail"),
                    ("ADMIN_CHANGE_STATE", "Admin Change State"),
                    ("ADMIN_SET_TAG", "Admin Set Tag"),
                    ("ADMIN_ANALYTICS", "Admin Analytics"),
                    ("ADMIN_ANALYTICS_EXCHANGE", "Admin Analytics Exchange"),
                    ("ADMIN_ANALYTICS_MEMBERS", "Admin Analytics Members"),
                    ("ADMIN_REENGAGE", "Admin Re-engage"),
                    ("ADMIN_REENGAGE_AUDIENCE", "Admin Re-engage Audience"),
                    ("ADMIN_REENGAGE_COMPOSE", "Admin Re-engage Compose"),
                    ("ADMIN_REENGAGE_SCHEDULE", "Admin Re-engage Schedule"),
                    ("ADMIN_OFFER_CREATE", "Admin Offer Create"),
                ],
                default="START",
                max_length=64,
                verbose_name="State",
            ),
        ),
        migrations.AddIndex(
            model_name="customerprofile",
            index=models.Index(fields=["tag"], name="customerprofile_tag_idx"),
        ),
        migrations.AddIndex(
            model_name="botsession",
            index=models.Index(
                fields=["bot", "last_activity"],
                name="botsess_bot_activity_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="exchangerequest",
            index=models.Index(
                fields=["bot", "status", "created_at"],
                name="exreq_bot_stat_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="exchangerequest",
            index=models.Index(
                fields=["customer", "created_at"],
                name="exreq_cust_created_idx",
            ),
        ),
    ]
