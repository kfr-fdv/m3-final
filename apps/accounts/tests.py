import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User


@pytest.mark.parametrize("login", ["alice@example.com", "ALICE@example.com", "alice"])
def test_login_by_email_or_username(client: Client, user: User, login: str) -> None:
    response = client.post(
        reverse("accounts:login"), {"username": login, "password": "secret-pass-123"}
    )

    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)


def test_login_with_wrong_password(client: Client, user: User) -> None:
    response = client.post(reverse("accounts:login"), {"username": "alice", "password": "nope"})

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_register_logs_in(client: Client, db) -> None:
    client.post(
        reverse("accounts:register"), {"email": "New@Example.com", "password": "Very-secret-777"}
    )

    assert User.objects.get().email == "new@example.com"
    assert "_auth_user_id" in client.session


def test_account_page_saves_profile(client: Client, user: User) -> None:
    client.force_login(user)

    client.post(
        reverse("accounts:profile"),
        {
            "last_name": "Шевченко",
            "first_name": "Аліса",
            "middle_name": "Петрівна",
            "email": "alice@example.com",
            "phone": "+380991112233",
        },
    )

    user.refresh_from_db()
    assert user.get_full_name() == "Шевченко Аліса Петрівна"
    assert user.phone == "+380991112233"


PROFILE = {
    "last_name": "Шевченко",
    "first_name": "Аліса",
    "email": "alice@example.com",
    "phone": "0991112233",
}
DELIVERY = {
    "city_name": "Київ (Київська обл.)",
    "city_ref": "city-kyiv",
    "delivery_type": "branch",
    "warehouse_name": "Відділення №1",
    "warehouse_ref": "wh-1",
}


def test_account_saves_nova_poshta_delivery(client: Client, user: User, nova_poshta) -> None:
    client.force_login(user)

    client.post(reverse("accounts:profile"), PROFILE | DELIVERY)

    user.refresh_from_db()
    assert (user.np_city_ref, user.np_warehouse_ref) == ("city-kyiv", "wh-1")
    # the branch name is taken from the API, not from the browser
    assert user.np_warehouse_name == "Відділення №1: вул. Пирогівський шлях, 135"
    assert user.phone == "+380991112233"


def test_delivery_is_optional_in_account(client: Client, user: User) -> None:
    client.force_login(user)

    response = client.post(reverse("accounts:profile"), PROFILE)

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.np_warehouse_ref == ""


def test_city_without_branch_is_an_error(client: Client, user: User, nova_poshta) -> None:
    client.force_login(user)

    response = client.post(
        reverse("accounts:profile"),
        PROFILE | DELIVERY | {"warehouse_ref": "", "warehouse_name": ""},
    )

    assert "warehouse_name" in response.context["form"].errors
