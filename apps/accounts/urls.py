from django.urls import path

from .views import (
    AccountView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("", AccountView.as_view(), name="profile"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("forgot-password/", PasswordResetView.as_view(), name="password_reset"),
    path(
        "reset/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
