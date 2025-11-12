from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from .forms import LoginForm
from django.contrib.auth import logout
from django.shortcuts import redirect


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/dashboard.html'
    login_url = reverse_lazy('accounts:login')


def logout_view(request):
    """Log out the user and redirect to the login page.

    Prefer POST for logout in templates/forms, but accept GET to simplify navigation.
    """
    logout(request)
    return redirect('accounts:login')
