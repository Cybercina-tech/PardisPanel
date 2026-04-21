from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """Redirect anonymous users to login for all pages except LOGIN_URL and admin.

    Use with caution — ensure static and media urls are allowed through.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = settings.LOGIN_URL
        self.public_prefixes = (
            "/admin/",
            "/static/",
            "/media/",
            "/prices/live-json/",
        )

    def __call__(self, request):
        path = request.path_info
        if not request.user.is_authenticated:
            is_public_path = path.startswith(self.login_url) or any(
                path.startswith(prefix) for prefix in self.public_prefixes
            )
            if not is_public_path:
                return redirect(self.login_url)
        return self.get_response(request)
