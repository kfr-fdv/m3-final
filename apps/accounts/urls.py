from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    ProfileView,
    RegisterView,
)

app_name = "accounts"

urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password/", PasswordChangeView.as_view(), name="password_change"),
    path("password/done/", PasswordChangeDoneView.as_view(), name="password_change_done"),
]
