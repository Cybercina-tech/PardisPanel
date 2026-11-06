"""Open a desk for customer users that predate per-account isolation.

Scoping fails closed, so a ``CustomUser`` with ``account_id`` NULL reads every
scoped table as empty — a connected Telegram bot reports as "no bot connected"
— and cannot write at all, since ``account`` is non-null on every scoped model.
Staff, super_admins and developers are account-less on purpose and stay so.
"""

from django.db import migrations


def _unique_slug(Account, user):
    base = (user.username or user.email or "account").lower().strip().replace(" ", "-")[:120]
    candidate, n = base, 1
    while Account.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def backfill(apps, schema_editor):
    Account = apps.get_model("accounts", "Account")
    CustomUser = apps.get_model("accounts", "CustomUser")

    orphans = CustomUser.objects.filter(
        account__isnull=True,
        is_staff=False,
        is_superuser=False,
    ).exclude(role__in=("super_admin", "developer")).order_by("pk")

    # Delegated operators inherit their owner's desk, so settle owners first.
    for user in list(orphans.filter(owner__isnull=True)):
        user.account = Account.objects.create(
            name=user.exchange_name or user.full_name or user.username,
            slug=_unique_slug(Account, user),
        )
        user.save(update_fields=["account"])

    for user in list(orphans.filter(owner__isnull=False)):
        owner_account_id = getattr(user.owner, "account_id", None)
        if owner_account_id is None:
            owner_account_id = Account.objects.create(
                name=user.owner.exchange_name or user.owner.full_name or user.owner.username,
                slug=_unique_slug(Account, user.owner),
            ).pk
            CustomUser.objects.filter(pk=user.owner_id).update(account_id=owner_account_id)
        CustomUser.objects.filter(pk=user.pk).update(account_id=owner_account_id)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_customuser_google_sub"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
