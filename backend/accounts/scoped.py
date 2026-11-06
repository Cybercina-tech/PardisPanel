"""Re-pin the account scope once DRF knows who is calling.

Django middleware runs *before* DRF resolves ``request.user``: the API is
JWT-only, so :class:`accounts.middleware.AccountScopeMiddleware` decodes the
bearer token itself to get a scope in place early. That covers token requests,
but not a session-authenticated view or a view driven straight off
``APIRequestFactory``, both of which install the user inside the view.

Rather than ask every view to remember a mixin — where one omission is a
cross-tenant leak — the hook is installed once on ``APIView``: ``initial`` pins
the scope after authentication, and ``dispatch`` unwinds it in a ``finally`` so
a view reached without the middleware (a factory-built request, an ASGI hop)
cannot strand one caller's account in the context for the next one.
"""

from .middleware import account_scope_for_user
from .scoping import reset_current_account, set_current_account_id

_installed = False


def install():
    global _installed
    if _installed:
        return
    _installed = True

    from rest_framework.views import APIView

    original_dispatch = APIView.dispatch
    original_initial = APIView.initial

    def dispatch(self, request, *args, **kwargs):
        self._account_scope_token = None
        try:
            return original_dispatch(self, request, *args, **kwargs)
        finally:
            token = self._account_scope_token
            self._account_scope_token = None
            if token is not None:
                try:
                    reset_current_account(token)
                except ValueError:
                    pass

    def initial(self, request, *args, **kwargs):
        original_initial(self, request, *args, **kwargs)
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            self._account_scope_token = set_current_account_id(
                account_scope_for_user(user)
            )

    APIView.dispatch = dispatch
    APIView.initial = initial
