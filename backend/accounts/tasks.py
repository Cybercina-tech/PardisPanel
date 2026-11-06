from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task
def expire_trials_task():
    """Deactivate accounts whose trial has been over for the whole grace window.

    Day 14 itself is already enforced live by TrialAccessMiddleware, so this
    task is the later, harder lock. Holding it back by TRIAL_GRACE_DAYS gives
    sales a window in which a customer can still log in, see the upgrade
    prompt and be converted with their data intact.

    ``trial_expiry_notified_at`` belongs to the pre-expiry reminder in
    fleet.tasks and is deliberately not touched here.
    """
    from .models import CustomUser

    now = timezone.now()
    cutoff = now - timedelta(days=getattr(settings, "TRIAL_GRACE_DAYS", 7))
    users = CustomUser.objects.filter(
        is_active=True,
        trial_expires_at__isnull=False,
        trial_expires_at__lte=cutoff,
    ).exclude(role=CustomUser.ROLE_SUPER_ADMIN).exclude(is_superuser=True)
    count = users.update(is_active=False)
    return {"deactivated": count}
