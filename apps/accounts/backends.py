from typing import Any

from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

from .models import User


class EmailBackend(ModelBackend):
    """Log in with email and password. Login by username is handled by ModelBackend."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> User | None:
        if not username or not password:
            return None
        user = User.objects.filter(email__iexact=username).order_by("pk").first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
