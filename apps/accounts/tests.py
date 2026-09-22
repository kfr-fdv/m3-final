import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_register_creates_user_and_logs_in(client):
    response = client.post(
        reverse("accounts:register"),
        {
            "username": "newbie",
            "email": "newbie@example.com",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        },
    )
    assert response.status_code == 302
    assert User.objects.filter(username="newbie").exists()
    assert client.session.get("_auth_user_id")


def test_login_and_profile_update(client, user):
    client.force_login(user)
    response = client.post(
        reverse("accounts:profile"),
        {
            "first_name": "Alice",
            "last_name": "A",
            "email": "a@e.com",
            "phone": "42",
            "default_address": "Home",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.phone == "42"
    assert user.default_address == "Home"


def test_profile_requires_login(client):
    response = client.get(reverse("accounts:profile"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_password_change(client, user):
    client.force_login(user)
    response = client.post(
        reverse("accounts:password_change"),
        {
            "old_password": "secret-pass-123",
            "new_password1": "BrandNewPass456!",
            "new_password2": "BrandNewPass456!",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.check_password("BrandNewPass456!")
