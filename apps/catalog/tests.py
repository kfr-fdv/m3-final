from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.reviews.models import Review


@pytest.fixture
def shop(db) -> dict[str, Product]:
    hops = Category.objects.create(name="Hops", slug="hops")
    aroma = Category.objects.create(name="Aroma Hops", slug="aroma-hops", parent=hops)
    yeast = Category.objects.create(name="Yeast", slug="yeast")
    return {
        "citra": Product.objects.create(
            name="Citra", category=aroma, price=Decimal("6"), stock=5, description="tropical"
        ),
        "saaz": Product.objects.create(name="Saaz", category=hops, price=Decimal("4"), stock=0),
        "us05": Product.objects.create(name="US-05", category=yeast, price=Decimal("3"), stock=9),
        "old": Product.objects.create(
            name="Old", category=yeast, price=Decimal("1"), is_active=False
        ),
    }


def names(client: Client, **params) -> list[str]:
    response = client.get(reverse("catalog:product_list"), params)
    return [product.name for product in response.context["products"]]


def test_list_shows_only_active_products(client: Client, shop) -> None:
    assert sorted(names(client)) == ["Citra", "Saaz", "US-05"]


def test_root_category_includes_subcategories(client: Client, shop) -> None:
    assert sorted(names(client, category="hops")) == ["Citra", "Saaz"]


def test_several_categories(client: Client, shop) -> None:
    assert sorted(names(client, category=["aroma-hops", "yeast"])) == ["Citra", "US-05"]


def test_search_in_name_and_description(client: Client, shop) -> None:
    assert names(client, search="TROPICAL") == ["Citra"]
    assert names(client, search="saaz") == ["Saaz"]


def test_price_range_and_stock(client: Client, shop) -> None:
    assert sorted(names(client, min_price=3.5, max_price=6)) == ["Citra", "Saaz"]
    assert sorted(names(client, in_stock="true")) == ["Citra", "US-05"]


@pytest.mark.parametrize(
    ("ordering", "expected"),
    [("price", ["US-05", "Saaz", "Citra"]), ("-price", ["Citra", "Saaz", "US-05"])],
)
def test_sort_by_price(client: Client, shop, ordering: str, expected: list[str]) -> None:
    assert names(client, ordering=ordering) == expected


def test_sort_by_rating(client: Client, shop) -> None:
    user = User.objects.create_user(username="u", password="secret-pass-123")
    Review.objects.create(user=user, product=shop["us05"], rating=5)
    Review.objects.create(user=user, product=shop["saaz"], rating=2)

    assert names(client, ordering="-rating")[:2] == ["US-05", "Saaz"]


def test_pagination_keeps_filters(client: Client, category: Category) -> None:
    for number in range(13):
        Product.objects.create(name=f"Hop {number}", category=category, price=1, stock=1)

    first = client.get(reverse("catalog:product_list"), {"category": "hops"})
    second = client.get(reverse("catalog:product_list"), {"category": "hops", "page": "2"})

    assert len(first.context["products"]) == 12
    assert len(second.context["products"]) == 1
    assert "category=hops" in first.content.decode()


def test_product_page(client: Client, shop) -> None:
    assert client.get(shop["citra"].get_absolute_url()).status_code == 200


def test_hidden_product_page_is_404(client: Client, shop) -> None:
    assert client.get(shop["old"].get_absolute_url()).status_code == 404
