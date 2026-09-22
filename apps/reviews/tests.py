import pytest
from django.urls import reverse

from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review
from apps.reviews.services import user_can_review

pytestmark = pytest.mark.django_db


def _buy(user, product, status=Order.OrderStatus.PAID):
    order = Order.objects.create(user=user, shipping_address="a", status=status)
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
    return order


def test_cannot_review_without_purchase(user, product):
    assert user_can_review(user, product) is False


def test_can_review_after_purchase(user, product):
    _buy(user, product)
    assert user_can_review(user, product) is True


def test_cannot_review_twice(user, product):
    _buy(user, product)
    Review.objects.create(product=product, user=user, rating=5, comment="great")
    assert user_can_review(user, product) is False


def test_review_create_view_blocks_without_purchase(client, user, product):
    client.force_login(user)
    response = client.post(
        reverse("reviews:create", args=[product.slug]), {"rating": 5, "comment": "x"}
    )
    assert response.status_code == 302
    assert Review.objects.count() == 0


def test_review_create_view_after_purchase(client, user, product):
    _buy(user, product)
    client.force_login(user)
    client.post(reverse("reviews:create", args=[product.slug]), {"rating": 4, "comment": "nice"})
    assert Review.objects.filter(product=product, user=user, rating=4).exists()
