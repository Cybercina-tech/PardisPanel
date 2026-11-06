from datetime import timedelta

from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken


def issue_tokens_for_user(user, impersonator=None, remember=False):
    refresh = RefreshToken.for_user(user)
    if remember:
        # `remember` rides in the refresh token so rotation can keep the longer lifetime.
        refresh.set_exp(lifetime=timedelta(days=settings.REMEMBER_ME_REFRESH_DAYS))
        refresh["remember"] = True
    refresh.access_token["token_version"] = getattr(user, "token_version", 0)
    if impersonator is not None:
        refresh["impersonator_id"] = impersonator.id
        refresh["impersonator_username"] = impersonator.username
        refresh.access_token["impersonator_id"] = impersonator.id
        refresh.access_token["impersonator_username"] = impersonator.username
    return refresh
