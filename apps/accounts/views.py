from typing import Any

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView as DjangoLoginView,
)
from django.contrib.auth.views import (
    LogoutView as DjangoLogoutView,
)
from django.contrib.auth.views import (
    PasswordChangeDoneView as DjangoPasswordChangeDoneView,
)
from django.contrib.auth.views import (
    PasswordChangeView as DjangoPasswordChangeView,
)
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import ProfileForm, RegisterForm


class RegisterView(CreateView):
    """Реєстрація з автоматичним входом після створення акаунта."""

    template_name = "accounts/register.html"
    form_class = RegisterForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form: Any) -> HttpResponse:
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(DjangoLogoutView):
    pass


class ProfileView(LoginRequiredMixin, UpdateView):
    """Редагування профілю поточного користувача."""

    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset: Any = None) -> Any:
        return self.request.user


class PasswordChangeView(DjangoPasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class PasswordChangeDoneView(DjangoPasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"
