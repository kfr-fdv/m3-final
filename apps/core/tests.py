import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem

pytestmark = pytest.mark.django_db


def test_analytics_requires_staff(client, user):
    client.force_login(user)
    response = client.get(reverse("admin-analytics"))
    assert response.status_code == 302  # redirect to admin login


def test_analytics_shows_revenue(client, django_user_model, product, user):
    staff = django_user_model.objects.create_user("boss", password="x", is_staff=True)
    order = Order.objects.create(user=user, shipping_address="a", status=Order.OrderStatus.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=2, price=product.price)
    order.recalculate_total()

    client.force_login(staff)
    response = client.get(reverse("admin-analytics"))
    assert response.status_code == 200
    assert response.context["summary"]["revenue"] == product.price * 2
    assert response.context["summary"]["orders_count"] == 1


def test_seed_demo_is_idempotent(db):
    call_command("seed_demo")
    first = Product.objects.count()
    call_command("seed_demo")
    assert Product.objects.count() == first == 12
