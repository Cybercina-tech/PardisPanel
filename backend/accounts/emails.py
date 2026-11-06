"""Outgoing mail for self-serve signups.

Verification is deliberately stateless: a signed, timestamped payload carries
the user id and the address it was issued for, so changing the email or letting
the link age out invalidates it without a token table to prune.
"""
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

VERIFICATION_SALT = "accounts.email-verify"


def _public_base_url():
    configured = getattr(settings, "PUBLIC_BASE_URL", "")
    if configured:
        return configured
    for host in getattr(settings, "ALLOWED_HOSTS", []) or []:
        if host and "*" not in host:
            scheme = "http" if settings.DEBUG else "https"
            return f"{scheme}://{host}"
    return "http://localhost:8000"


def make_verification_token(user):
    return signing.dumps(
        {"uid": user.pk, "email": (user.email or "").lower()},
        salt=VERIFICATION_SALT,
    )


def read_verification_token(token):
    """Return the CustomUser the token points at, or None if it is not usable.

    Not usable covers every failure the caller treats identically: tampered,
    expired, pointing at a deleted or deactivated account, or issued for an
    address the account no longer has.
    """
    from .models import CustomUser

    try:
        payload = signing.loads(
            token,
            salt=VERIFICATION_SALT,
            max_age=getattr(settings, "EMAIL_VERIFICATION_TIMEOUT", 259200),
        )
    except signing.BadSignature:
        return None
    user = CustomUser.objects.filter(pk=payload.get("uid"), is_active=True).first()
    if user is None:
        return None
    if (user.email or "").lower() != payload.get("email"):
        return None
    return user


def verification_url(user):
    return f"{_public_base_url()}/verify-email/{make_verification_token(user)}"


def send_verification_email(user):
    """Best effort: a mail server problem must not cost the customer their signup."""
    if not getattr(settings, "SIGNUP_EMAIL_VERIFICATION", True):
        return False
    if not user.email:
        return False
    context = {
        "user": user,
        "verification_url": verification_url(user),
        "trial_days": getattr(settings, "INDIVIDUAL_TRIAL_DAYS", 14),
        "panel_url": f"{_public_base_url()}/panel",
    }
    try:
        subject = render_to_string("accounts/email/verify_subject.txt", context).strip()
        text_body = render_to_string("accounts/email/verify_body.txt", context)
        html_body = render_to_string("accounts/email/verify_body.html", context)
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception("signup: could not send the verification email to user %s", user.pk)
        return False


def mark_email_verified(user):
    if user.email_verified_at is not None:
        return False
    user.email_verified_at = timezone.now()
    user.save(update_fields=["email_verified_at"])
    return True
