import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review
from apps.reviews.services import can_review


def buy(user: User, product: Product, status: str = "delivered") -> None:
    order = Order.objects.create(user=user, shipping_address="Kyiv", status=status)
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)


def review_url(product: Product) -> str:
    return reverse("reviews:create", args=[product.slug])


def test_guest_cannot_review(product: Product) -> None:
    from django.contrib.auth.models import AnonymousUser

    assert not can_review(AnonymousUser(), product)


def test_only_buyers_can_review(user: User, product: Product) -> None:
    assert not can_review(user, product)
    buy(user, product)
    assert can_review(user, product)


@pytest.mark.parametrize("status", ["pending", "cancelled"])
def test_unpaid_order_does_not_count(user: User, product: Product, status: str) -> None:
    buy(user, product, status=status)

    assert not can_review(user, product)


def test_buyer_leaves_review(client: Client, user: User, product: Product) -> None:
    buy(user, product)
    client.force_login(user)

    client.post(review_url(product), {"rating": 4, "comment": "Nice aroma"})

    review = Review.objects.get()
    assert (review.user, review.rating, review.comment) == (user, 4, "Nice aroma")
    assert not can_review(user, product)


def test_second_review_is_rejected(client: Client, user: User, product: Product) -> None:
    buy(user, product)
    client.force_login(user)

    client.post(review_url(product), {"rating": 5})
    client.post(review_url(product), {"rating": 1})

    assert Review.objects.get().rating == 5


def test_not_a_buyer_cannot_post_review(client: Client, user: User, product: Product) -> None:
    client.force_login(user)

    client.post(review_url(product), {"rating": 5})

    assert not Review.objects.exists()


@pytest.mark.parametrize("rating", [0, 6, "x"])
def test_rating_must_be_from_1_to_5(client: Client, user: User, product: Product, rating) -> None:
    buy(user, product)
    client.force_login(user)

    client.post(review_url(product), {"rating": rating})

    assert not Review.objects.exists()


def test_product_page_shows_form_only_to_buyer(
    client: Client, user: User, product: Product
) -> None:
    client.force_login(user)
    assert not client.get(product.get_absolute_url()).context["can_review"]

    buy(user, product)
    assert client.get(product.get_absolute_url()).context["can_review"]


def test_rating_on_product_page(client: Client, user: User, product: Product) -> None:
    Review.objects.create(user=user, product=product, rating=4)
    other = User.objects.create_user(username="bob", password="secret-pass-123")
    Review.objects.create(user=other, product=product, rating=5)

    shown = client.get(product.get_absolute_url()).context["product"]

    assert (shown.rating_avg, shown.rating_count) == (4.5, 2)
