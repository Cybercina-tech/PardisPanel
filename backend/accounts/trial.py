from datetime import timedelta

from django.conf import settings
from django.utils import timezone

TRIAL_PLAN = "free_trial"


def trial_duration():
    """Trial length, from INDIVIDUAL_TRIAL_DAYS. Fixed at 14 days by default."""
    return timedelta(days=getattr(settings, "INDIVIDUAL_TRIAL_DAYS", 14))


def trial_expires_at(started_at):
    return started_at + trial_duration()


def trial_is_expired(user, now=None):
    if getattr(user, "is_superuser", False) or getattr(user, "role", "") == "super_admin":
        return False
    # A recorded sale flips the account to paid; the trial dates stay on the
    # user as history but stop gating anything.
    account = getattr(user, "account", None)
    if account is not None and getattr(account, "is_paid", False):
        return False
    expires_at = getattr(user, "trial_expires_at", None)
    return expires_at is not None and expires_at <= (now or timezone.now())


def ensure_trial_started(user, now=None):
    """Initialize a trial once for an ordinary account; never reset an existing trial."""
    if getattr(user, "role", "") == "super_admin" or getattr(user, "is_superuser", False):
        return False
    if user.trial_started_at is not None or user.trial_expires_at is not None:
        return False
    started = now or timezone.now()
    user.trial_started_at = started
    user.trial_expires_at = trial_expires_at(started)
    user.save(update_fields=["trial_started_at", "trial_expires_at"])
    return True
