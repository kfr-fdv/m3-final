from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.delivery.novaposhta import City, NovaPoshtaError, Warehouse


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="alice@example.com", password="secret-pass-123"
    )


@pytest.fixture
def staff_user(db) -> User:
    return User.objects.create_user(username="boss", password="secret-pass-123", is_staff=True)


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


# --- Nova Poshta without the network ------------------------------------------------

KYIV = City(ref="city-kyiv", name="Київ", area="Київська")
BRANCH_1 = Warehouse(
    ref="wh-1",
    city_ref="city-kyiv",
    city_name="Київ",
    number="1",
    name="Відділення №1: вул. Пирогівський шлях, 135",
    is_postomat=False,
)
POSTOMAT_5 = Warehouse(
    ref="wh-5",
    city_ref="city-kyiv",
    city_name="Київ",
    number="5",
    name='Поштомат "Нова Пошта" №5: вул. Хрещатик, 1',
    is_postomat=True,
)


class FakeNovaPoshta:
    """Answers like the real client, from the two warehouses above."""

    down = False

    def _check(self) -> None:
        if self.down:
            raise NovaPoshtaError("API is down")

    def search_cities(self, query: str, limit: int = 10) -> list[City]:
        self._check()
        return [KYIV] if query.lower() in KYIV.name.lower() else []

    def search_warehouses(
        self, city_ref: str, query: str = "", postomat: bool = False, limit: int = 20
    ) -> list[Warehouse]:
        self._check()
        return [
            w
            for w in (BRANCH_1, POSTOMAT_5)
            if w.city_ref == city_ref and w.is_postomat == postomat
        ]

    def get_warehouse(self, ref: str) -> Warehouse | None:
        self._check()
        return {w.ref: w for w in (BRANCH_1, POSTOMAT_5)}.get(ref)


@pytest.fixture
def nova_poshta(monkeypatch) -> FakeNovaPoshta:
    fake = FakeNovaPoshta()
    monkeypatch.setattr("apps.delivery.forms.get_client", lambda: fake)
    monkeypatch.setattr("apps.delivery.views.get_client", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def _clear_cache():
    """Cached Nova Poshta answers must not leak between tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
