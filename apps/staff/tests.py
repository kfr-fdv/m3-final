from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem


@pytest.fixture
def staff(client: Client, staff_user: User) -> Client:
    client.force_login(staff_user)
    return client


@pytest.mark.parametrize("name", ["staff:products", "staff:product_add", "staff:dashboard"])
def test_customers_cannot_open_staff_pages(client: Client, user: User, name: str) -> None:
    client.force_login(user)

    assert client.get(reverse(name)).status_code == 403


def test_product_list_shows_hidden_products(staff: Client, product: Product) -> None:
    Product.objects.filter(pk=product.pk).update(is_active=False)

    response = staff.get(reverse("staff:products"))

    assert list(response.context["products"]) == [product]


def test_create_product(staff: Client, category: Category) -> None:
    response = staff.post(
        reverse("staff:product_add"),
        {
            "name": "Saaz Hops",
            "description": "Czech",
            "price": "4.50",
            "stock": 5,
            "category": category.pk,
        },
    )

    product = Product.objects.get(name="Saaz Hops")
    assert response["Location"] == reverse("staff:product_edit", args=[product.pk])
    assert (product.slug, product.price, product.stock) == ("saaz-hops", Decimal("4.50"), 5)


def test_update_product(staff: Client, product: Product, category: Category) -> None:
    staff.post(
        reverse("staff:product_edit", args=[product.pk]),
        {"name": "Citra Hops", "price": "6.49", "stock": 3, "category": category.pk},
    )

    product.refresh_from_db()
    assert (product.price, product.stock) == (Decimal("6.49"), 3)


def test_hide_and_show_product(staff: Client, product: Product) -> None:
    url = reverse("staff:product_toggle", args=[product.pk])

    staff.post(url)
    product.refresh_from_db()
    assert not product.is_active

    staff.post(url)
    product.refresh_from_db()
    assert product.is_active


def test_delete_product(staff: Client, product: Product) -> None:
    response = staff.post(reverse("staff:product_delete", args=[product.pk]))

    assert response["Location"] == reverse("staff:products")
    assert not Product.objects.exists()


def test_product_with_orders_is_not_deleted(staff: Client, product: Product, user: User) -> None:
    order = Order.objects.create(user=user, shipping_address="Kyiv")
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)

    staff.post(reverse("staff:product_delete", args=[product.pk]))

    assert Product.objects.filter(pk=product.pk).exists()


def test_dashboard_counts_sales_without_cancelled(
    staff: Client, user: User, product: Product
) -> None:
    for status in ("paid", "pending", "cancelled"):
        order = Order.objects.create(user=user, shipping_address="Kyiv", status=status)
        OrderItem.objects.create(order=order, product=product, quantity=1, price=Decimal("10"))

    cards = {card["key"]: card for card in staff.get(reverse("staff:dashboard")).context["cards"]}

    assert cards["sales"]["value"] == Decimal("20")
    assert cards["orders"]["value"] == 3
    assert cards["pending"]["value"] == 1
