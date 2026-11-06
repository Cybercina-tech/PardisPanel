# Generated manually for Admin Panel Analytics V1

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("telegram_app", "0009_exchange_request_cancelled_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="telegramchannel",
            name="bot_admin_verified",
            field=models.BooleanField(
                default=False,
                help_text="Whether the bot was an administrator at the last snapshot.",
                verbose_name="Bot Admin Verified",
            ),
        ),
        migrations.AddField(
            model_name="telegramchannel",
            name="last_member_count",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Cached subscriber count from the latest snapshot job.",
                null=True,
                verbose_name="Last Member Count",
            ),
        ),
        migrations.AddField(
            model_name="telegramchannel",
            name="last_member_sampled_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="Last Member Sampled At",
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
        migrations.CreateModel(
            name="BotDailyUsageSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(db_index=True, verbose_name="Date")),
                (
                    "active_users",
                    models.PositiveIntegerField(default=0, verbose_name="Active Users"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_usage_snapshots",
                        to="telegram_app.telegrambot",
                        verbose_name="Bot",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bot Daily Usage Snapshot",
                "verbose_name_plural": "Bot Daily Usage Snapshots",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="BotCustomerGrowthSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(db_index=True, verbose_name="Date")),
                (
                    "new_customers",
                    models.PositiveIntegerField(default=0, verbose_name="New Customers"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_growth_snapshots",
                        to="telegram_app.telegrambot",
                        verbose_name="Bot",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bot Customer Growth Snapshot",
                "verbose_name_plural": "Bot Customer Growth Snapshots",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="ChannelMemberSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("member_count", models.PositiveIntegerField(verbose_name="Member Count")),
                (
                    "bot_is_admin",
                    models.BooleanField(default=False, verbose_name="Bot Is Admin"),
                ),
                (
                    "sampled_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="Sampled At"
                    ),
                ),
                (
                    "channel",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="member_snapshots",
                        to="telegram_app.telegramchannel",
                        verbose_name="Channel",
                    ),
                ),
            ],
            options={
                "verbose_name": "Channel Member Snapshot",
                "verbose_name_plural": "Channel Member Snapshots",
                "ordering": ["-sampled_at"],
            },
        ),
        migrations.CreateModel(
            name="ReengageCampaign",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("vip", "VIP"),
                            ("special", "Special"),
                            ("inactive", "Inactive"),
                        ],
                        max_length=16,
                        verbose_name="Audience",
                    ),
                ),
                ("message", models.TextField(verbose_name="Message")),
                (
                    "schedule",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                        ],
                        default="weekly",
                        max_length=16,
                        verbose_name="Schedule",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                (
                    "next_run_at",
                    models.DateTimeField(db_index=True, verbose_name="Next Run At"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reengage_campaigns",
                        to="telegram_app.telegrambot",
                        verbose_name="Bot",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reengage_campaigns",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Re-engage Campaign",
                "verbose_name_plural": "Re-engage Campaigns",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ReengageOffer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255, verbose_name="Title")),
                ("body", models.TextField(verbose_name="Body")),
                (
                    "audience",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("vip", "VIP"),
                            ("special", "Special"),
                            ("inactive", "Inactive"),
                        ],
                        default="global",
                        max_length=16,
                        verbose_name="Audience",
                    ),
                ),
                (
                    "valid_until",
                    models.DateTimeField(blank=True, null=True, verbose_name="Valid Until"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reengage_offers",
                        to="telegram_app.telegrambot",
                        verbose_name="Bot",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reengage_offers",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Re-engage Offer",
                "verbose_name_plural": "Re-engage Offers",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="CampaignDeliveryLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("sent", models.PositiveIntegerField(default=0, verbose_name="Sent")),
                ("failed", models.PositiveIntegerField(default=0, verbose_name="Failed")),
                (
                    "skipped",
                    models.PositiveIntegerField(default=0, verbose_name="Skipped"),
                ),
                (
                    "run_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="Run At"
                    ),
                ),
                (
                    "bot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campaign_delivery_logs",
                        to="telegram_app.telegrambot",
                        verbose_name="Bot",
                    ),
                ),
                (
                    "campaign",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="delivery_logs",
                        to="telegram_app.reengagecampaign",
                        verbose_name="Campaign",
                    ),
                ),
                (
                    "offer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="delivery_logs",
                        to="telegram_app.reengageoffer",
                        verbose_name="Offer",
                    ),
                ),
            ],
            options={
                "verbose_name": "Campaign Delivery Log",
                "verbose_name_plural": "Campaign Delivery Logs",
                "ordering": ["-run_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="botdailyusagesnapshot",
            constraint=models.UniqueConstraint(
                fields=("bot", "date"),
                name="unique_bot_daily_usage_per_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="botcustomergrowthsnapshot",
            constraint=models.UniqueConstraint(
                fields=("bot", "date"),
                name="unique_bot_customer_growth_per_date",
            ),
        ),
    ]
