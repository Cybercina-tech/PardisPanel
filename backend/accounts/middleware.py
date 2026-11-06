from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from .scoping import (
    UNSCOPED,
    account_for_user,
    reset_current_account,
    set_current_account_id,
)
from .trial import trial_is_expired

# Methods that only read. An expired trial keeps its data visible so the
# customer can see what they are about to lose; only writes are walled off.
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def resolve_request_user(request):
    """The authenticated user behind a request, session or JWT.

    DRF authenticates inside the view, long after middleware has run, and the
    API is JWT-only — so ``request.user`` from ``AuthenticationMiddleware`` is
    anonymous for every API call that does not also carry a session cookie.
    Middleware that must know who is calling has to decode the bearer token
    itself. The result is cached on the request so the later DRF pass and any
    other middleware share one decode and one user fetch.
    """
    if hasattr(request, "_resolved_user"):
        return request._resolved_user

    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        try:
            from .auth import JWTAuthenticationWithTokenVersion

            result = JWTAuthenticationWithTokenVersion().authenticate(request)
            user = result[0] if result else None
        except Exception:
            # A bad, expired or invalidated token is not this layer's problem:
            # DRF will reject it with the right status. Here it simply means
            # "nobody", which scopes to nothing and blocks no writes.
            user = None

    request._resolved_user = user
    return user


def account_scope_for_user(user):
    """The scope value a user should run under.

    Staff, super_admins and developers work across every customer, which is
    what lets the owner console query without a bypass at each call site.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False) or getattr(user, "role", "") in (
        "super_admin",
        "developer",
    ):
        # A super admin bound to an account (the Pardis install has exactly one
        # desk) works inside it, so everything they create gets that account.
        # Unbound ones stay global: they can read everywhere but cannot write
        # account-scoped rows, which is what the owner console wants.
        bound = getattr(user, "account_id", None)
        return bound if bound is not None else UNSCOPED
    account_id = account_for_user(user)
    if account_id is not None:
        return account_id
    # A desk user with no Account scopes to nothing, so every page reads as
    # empty and every write fails the non-null ``account`` column. Open the
    # desk here rather than leaving the customer with a panel that silently
    # shows none of their own data.
    ensure_account = getattr(user, "ensure_account", None)
    if callable(ensure_account):
        return ensure_account()
    return None


class AccountScopeMiddleware(MiddlewareMixin):
    """Pin the request's account so scoped managers narrow to it."""

    def process_request(self, request):
        request._account_scope_token = None
        # Set as early as possible so even a view that queries before DRF
        # authentication runs sees the right scope.
        user = resolve_request_user(request)
        request._account_scope_token = set_current_account_id(
            account_scope_for_user(user)
        )
        return None

    def process_response(self, request, response):
        token = getattr(request, "_account_scope_token", None)
        if token is not None:
            try:
                reset_current_account(token)
            except ValueError:
                # Token from a different context (async hop); the ContextVar
                # goes out of scope with the request anyway.
                pass
            request._account_scope_token = None
        return response


class TrialAccessMiddleware(MiddlewareMixin):
    """Wall off writes once a customer's free trial has run out.

    Reads stay open deliberately: an expired customer can still log in, see
    their prices and read the upgrade message. Only unsafe methods are refused,
    so the panel degrades to read-only rather than locking the door.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        user = resolve_request_user(request)
        path = request.path or ""
        if (
            user
            and user.is_authenticated
            and request.method not in SAFE_METHODS
            and trial_is_expired(user)
            and path.startswith("/api/")
            and not path.startswith(("/api/auth/", "/api/public/"))
        ):
            from setting.support import support_channel_payload

            return JsonResponse(
                {
                    "error": True,
                    "message": (
                        "Your free trial has ended. Your data is safe and still "
                        "visible, but changes are paused until you upgrade."
                    ),
                    "code": "trial_expired",
                    "support_channels": support_channel_payload(),
                },
                status=403,
            )
        return None


class LoginRequiredMiddleware(MiddlewareMixin):
    """Existing compatibility middleware; public/API auth views remain exempt."""

    PUBLIC_PREFIXES = (
        "/login",
        "/signup",
        "/tutorials",
        "/static/",
        "/media/",
        "/api/auth/",
        "/api/public/",
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith(self.PUBLIC_PREFIXES):
            return None
        return None
