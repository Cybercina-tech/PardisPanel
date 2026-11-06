"""Server-side verification of Google id-tokens.

The browser sends the id-token it got from Google Identity Services and this
module checks Google's signature, issuer and audience before anything is
trusted. Verifying client-side would mean accepting whatever the page claimed.
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


def google_enabled():
    return bool(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", ""))


def verify_id_token(token):
    """The token's claims, or ``None`` when it is not a valid, verified sign-in.

    Only a token issued by Google, for this client id, carrying a verified
    email address gets through — an unverified address would let anyone who can
    create a Google account claim someone else's inbox.
    """
    if not google_enabled() or not token:
        return None
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token

        claims = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except Exception:
        # Never log the token: it is a bearer credential until it expires.
        logger.warning("google: id-token verification failed")
        return None

    if claims.get("iss") not in _ISSUERS:
        return None
    if not claims.get("email") or not claims.get("email_verified"):
        return None
    if not claims.get("sub"):
        return None
    return claims
