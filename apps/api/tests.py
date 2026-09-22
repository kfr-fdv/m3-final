import pytest
from django.urls import reverse

from apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


def _token(api_client, username="alice", password="secret-pass-123"):
    response = api_client.post(
        reverse("api:login"), {"username": username, "password": password}, format="json"
    )
    return response.data["access"]


def test_products_list_and_detail(api_client, product):
    assert api_client.get(reverse("api:product-list")).status_code == 200
    assert api_client.get(reverse("api:product-detail", args=[product.id])).status_code == 200


def test_register_and_jwt_login(api_client):
    assert (
        api_client.post(
            reverse("api:register"),
            {"username": "apiuser", "email": "a@e.com", "password": "StrongPass123!"},
            format="json",
        ).status_code
        == 201
    )
    response = api_client.post(
        reverse("api:login"), {"username": "apiuser", "password": "StrongPass123!"}, format="json"
    )
    assert response.status_code == 200
    assert "access" in response.data and "refresh" in response.data


def test_order_create_and_ownership(api_client, product, user, django_user_model):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer " + _token(api_client, user.username))
    response = api_client.post(
        reverse("api:order-list"),
        {
            "full_name": "Alice",
            "email": "a@e.com",
            "phone": "5",
            "shipping_address": "addr",
            "payment_method": "card",
            "items": [{"product": product.id, "quantity": 2}],
        },
        format="json",
    )
    assert response.status_code == 201
    order_id = response.data["id"]
    product.refresh_from_db()
    assert product.stock == 8

    # other user cannot see it
    django_user_model.objects.create_user("bob", password="secret-pass-123")
    other = type(api_client)()
    other.credentials(HTTP_AUTHORIZATION="Bearer " + _token(other, "bob"))
    assert other.get(reverse("api:order-detail", args=[order_id])).status_code == 404


def test_order_create_rejects_over_stock(api_client, product, user):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer " + _token(api_client, user.username))
    response = api_client.post(
        reverse("api:order-list"),
        {
            "full_name": "A",
            "email": "a@e.com",
            "phone": "5",
            "shipping_address": "addr",
            "payment_method": "card",
            "items": [{"product": product.id, "quantity": 999}],
        },
        format="json",
    )
    assert response.status_code == 400


def test_review_api_requires_purchase(api_client, product, user):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer " + _token(api_client, user.username))
    url = reverse("api:product-reviews", args=[product.id])
    assert api_client.post(url, {"rating": 5, "comment": "x"}, format="json").status_code == 403

    order = Order.objects.create(user=user, shipping_address="a", status=Order.OrderStatus.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
    assert api_client.post(url, {"rating": 5, "comment": "ok"}, format="json").status_code == 201


def test_cart_api(api_client, product):
    assert (
        api_client.post(
            reverse("api:cart"), {"product": product.id, "quantity": 2}, format="json"
        ).status_code
        == 200
    )
    response = api_client.get(reverse("api:cart"))
    assert response.data["total"] == product.price * 2
