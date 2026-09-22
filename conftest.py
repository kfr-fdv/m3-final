from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import Category, Product


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="alice", password="secret-pass-123")


@pytest.fixture
def category(db) -> Category:
    return Category.objects.create(name="Hops", slug="hops")


@pytest.fixture
def product(category: Category) -> Product:
    return Product.objects.create(
        category=category,
        name="Citra Hops",
        slug="citra-hops",
        price=Decimal("5.99"),
        stock=10,
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()
