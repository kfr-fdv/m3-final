from decimal import Decimal

import pytest
from django.urls import reverse

from apps.catalog.filters import ProductFilter
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

pytestmark = pytest.mark.django_db


def test_search_matches_name_and_description(category):
    match = Product.objects.create(
        category=category,
        name="Citra",
        slug="citra",
        price=Decimal("5"),
        stock=1,
        description="tropical citrus",
    )
    Product.objects.create(
        category=category,
        name="Saaz",
        slug="saaz",
        price=Decimal("5"),
        stock=1,
        description="noble",
    )
    result = ProductFilter({"search": "citrus"}, queryset=Product.objects.for_listing()).qs
    assert list(result) == [match]


def test_category_filter_includes_descendants(category):
    child = Category.objects.create(name="Aroma", slug="aroma", parent=category)
    product = Product.objects.create(
        category=child, name="Mosaic", slug="mosaic", price=Decimal("5"), stock=1
    )
    result = ProductFilter({"category": "hops"}, queryset=Product.objects.for_listing()).qs
    assert product in list(result)


def test_with_rating_and_sold_annotations(product, user):
    Review.objects.create(product=product, user=user, rating=4, comment="ok")
    order = Order.objects.create(user=user, shipping_address="a", status=Order.OrderStatus.PAID)
    OrderItem.objects.create(order=order, product=product, quantity=3, price=product.price)

    annotated = Product.objects.for_listing().get(pk=product.pk)
    assert annotated.rating_avg == 4
    assert annotated.rating_count == 1
    assert annotated.sold_qty == 3


def test_cancelled_orders_not_counted_in_sold(product, user):
    order = Order.objects.create(
        user=user, shipping_address="a", status=Order.OrderStatus.CANCELLED
    )
    OrderItem.objects.create(order=order, product=product, quantity=3, price=product.price)
    annotated = Product.objects.for_listing().get(pk=product.pk)
    assert annotated.sold_qty == 0


def test_product_list_pagination(category, client):
    for i in range(15):
        Product.objects.create(
            category=category, name=f"P{i}", slug=f"p{i}", price=Decimal("1"), stock=1
        )
    response = client.get(reverse("catalog:product_list"))
    assert response.status_code == 200
    assert len(response.context["products"]) == 12


def test_product_detail_context(product, client):
    response = client.get(product.get_absolute_url())
    assert response.status_code == 200
    assert "cart_form" in response.context
    assert response.context["can_review"] is False


def test_inactive_product_hidden_from_listing(product):
    product.is_active = False
    product.save()
    assert product not in list(Product.objects.for_listing())
