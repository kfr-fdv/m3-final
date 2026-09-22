import pytest
from django.core import mail
from django.urls import reverse

from apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


def test_cart_add_and_view(client, product):
    client.post(reverse("orders:cart_add", args=[product.id]), {"quantity": 2})
    response = client.get(reverse("orders:cart"))
    assert response.status_code == 200
    assert response.context["total"] == product.price * 2
    assert not response.context["is_empty"]


def test_cart_add_clamped_to_stock(client, product):
    client.post(reverse("orders:cart_add", args=[product.id]), {"quantity": 999})
    assert client.session["cart"][str(product.id)] == product.stock


def test_cart_update_and_remove(client, product):
    client.post(reverse("orders:cart_add", args=[product.id]), {"quantity": 1})
    client.post(reverse("orders:cart_update", args=[product.id]), {"quantity": 4})
    assert client.session["cart"][str(product.id)] == 4
    client.post(reverse("orders:cart_remove", args=[product.id]))
    assert str(product.id) not in client.session["cart"]


def test_checkout_creates_order_decrements_stock_sends_email(client, product, user):
    client.force_login(user)
    client.post(reverse("orders:cart_add", args=[product.id]), {"quantity": 2})
    response = client.post(
        reverse("orders:checkout"),
        {
            "full_name": "Alice",
            "email": "alice@example.com",
            "phone": "555",
            "shipping_address": "1 Beer St",
            "payment_method": "card",
        },
    )
    order = Order.objects.get(user=user)
    assert response.status_code == 302
    assert order.total_price == product.price * 2
    assert order.items.count() == 1
    product.refresh_from_db()
    assert product.stock == 8
    assert client.session.get("cart") in (None, {})
    assert len(mail.outbox) == 2


def test_checkout_requires_login(client, product):
    client.post(reverse("orders:cart_add", args=[product.id]), {"quantity": 1})
    response = client.get(reverse("orders:checkout"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


def test_order_list_shows_only_own_orders(client, user, django_user_model):
    other = django_user_model.objects.create_user("bob", password="x")
    Order.objects.create(user=other, shipping_address="a")
    client.force_login(user)
    response = client.get(reverse("orders:order_list"))
    assert response.status_code == 200
    assert list(response.context["orders"]) == []


def test_order_detail_forbidden_for_non_owner(client, user, django_user_model):
    other = django_user_model.objects.create_user("bob", password="x")
    order = Order.objects.create(user=other, shipping_address="a")
    client.force_login(user)
    assert client.get(reverse("orders:order_detail", args=[order.id])).status_code == 404


def test_order_cancel_restocks(client, user, product):
    order = Order.objects.create(user=user, shipping_address="a", status=Order.OrderStatus.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=3, price=product.price)
    product.stock = 7
    product.save()
    client.force_login(user)
    client.post(reverse("orders:order_cancel", args=[order.id]))
    order.refresh_from_db()
    product.refresh_from_db()
    assert order.status == Order.OrderStatus.CANCELLED
    assert product.stock == 10
