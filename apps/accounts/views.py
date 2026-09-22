# Create your views here.
from django.views.generic import TemplateView


class ProfileView(TemplateView): ...


class LoginView(TemplateView): ...


class RegisterView(TemplateView): ...


class LogoutView(TemplateView): ...


class PasswordChangeView(TemplateView): ...
