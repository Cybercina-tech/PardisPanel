"""The account every test runs under.

Production code always runs inside a request, a Celery task or a management
command, each of which pins an account (or declares itself ``unscoped``). Tests
are the one caller that builds fixtures with no such context, and scoping fails
closed — so without a default the fixtures would be created account-less and
then be invisible to the very request the test makes.

Rather than rewrite two hundred ``setUp`` bodies, the whole suite runs inside
one shared account: fixtures are stamped with it on save, users created in a
test join it, and the middleware resolves those users back to it, so a test
reads exactly like single-tenant code. Isolation tests opt out explicitly with
``act_as_account`` or ``unscoped``.

The row is created once, right after the test database is migrated, so it sits
underneath every per-test transaction and no test can roll it away.
"""
from .scoping import set_default_account_id

TEST_ACCOUNT_SLUG = "test-account"


def create_and_pin_test_account():
    """Create the shared test account and make it the process-wide default."""
    from .models import Account

    account, _ = Account.objects.get_or_create(
        slug=TEST_ACCOUNT_SLUG, defaults={"name": "Test Account"}
    )
    set_default_account_id(account.pk)
    return account
