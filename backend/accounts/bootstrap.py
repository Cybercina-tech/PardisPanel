"""Backfill helper for the per-account isolation migrations.

Deployments that predate :class:`accounts.models.Account` hold rows that belong
to nobody. They are all one customer's — the operator who ran the panel before
it became multi-tenant — so they move onto a single bootstrap account, which is
what lets the ``account`` column become non-null.
"""

BOOTSTRAP_SLUG = "bootstrap"
BOOTSTRAP_NAME = "Bootstrap"


def bootstrap_account(apps):
    """The bootstrap account, created on first use."""
    Account = apps.get_model("accounts", "Account")
    account, _ = Account.objects.get_or_create(
        slug=BOOTSTRAP_SLUG, defaults={"name": BOOTSTRAP_NAME}
    )
    return account


def backfill_account(model_label):
    """A ``RunPython`` callable moving account-less rows onto the bootstrap account."""

    def migrate(apps, schema_editor):
        Model = apps.get_model(model_label)
        orphans = Model.objects.filter(account__isnull=True)
        if not orphans.exists():
            return
        orphans.update(account=bootstrap_account(apps))

    return migrate
