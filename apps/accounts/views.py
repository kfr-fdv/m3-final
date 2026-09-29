from typing import Any

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.forms import ModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, UpdateView

from apps.orders.models import Order

from .forms import ProfileForm, RegisterForm
from .models import User


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class RegisterView(FormView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("catalog:home")

    def form_valid(self, form: RegisterForm) -> HttpResponse:
        user = form.save()
        login(self.request, user, backend="apps.accounts.backends.EmailBackend")
        if not form.cleaned_data["remember_me"]:
            self.request.session.set_expiry(0)  # log out when the browser closes
        messages.success(self.request, "Вітаємо! Акаунт створено.")
        return super().form_valid(form)


class AccountView(LoginRequiredMixin, UpdateView):
    """One page with two tabs, as in the design: order history and account information."""

    form_class = ProfileForm
    template_name = "accounts/account.html"
    orders_per_page = 8

    def get_object(self, queryset: Any = None) -> User:
        return self.request.user  # type: ignore[return-value]

    def get_success_url(self) -> str:
        return reverse("accounts:profile") + "#account-info"

    def form_valid(self, form: "ModelForm[User]") -> HttpResponse:
        form.save()
        messages.success(self.request, "Дані збережено.")
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        orders = Order.objects.filter(user=self.object)
        context["orders_page"] = Paginator(orders, self.orders_per_page).get_page(
            self.request.GET.get("page")
        )
        return context


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/forgot_password.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form: Any) -> HttpResponse:
        messages.success(
            self.request,
            "Якщо цей email зареєстрований, ми надіслали на нього посилання для відновлення.",
        )
        return super().form_valid(form)


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/reset_password.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form: Any) -> HttpResponse:
        messages.success(self.request, "Пароль змінено. Увійдіть з новим паролем.")
        return super().form_valid(form)
