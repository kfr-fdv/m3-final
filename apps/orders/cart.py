from collections.abc import Iterator
from decimal import Decimal

from django.http import HttpRequest

from apps.catalog.models import Product

CART_SESSION_KEY = "cart"


class CartLine:
    """Один рядок кошика: товар та його кількість."""

    def __init__(self, product: Product, quantity: int) -> None:
        self.product = product
        self.quantity = quantity

    @property
    def line_total(self) -> Decimal:
        return self.product.price * self.quantity


class Cart:
    """Кошик, що зберігається в сесії користувача як {product_id: quantity}."""

    def __init__(self, request: HttpRequest) -> None:
        self.session = request.session
        self._cart: dict[str, int] = self.session.get(CART_SESSION_KEY, {})

    def _save(self) -> None:
        self.session[CART_SESSION_KEY] = self._cart
        self.session.modified = True

    def add(self, product: Product, quantity: int = 1, *, replace: bool = False) -> int:
        """Додає товар (або замінює кількість). Обмежує кількість наявним залишком.

        Повертає підсумкову кількість цього товару в кошику (0, якщо немає в наявності).
        """
        if product.stock <= 0:
            return 0
        pid = str(product.pk)
        current = self._cart.get(pid, 0)
        desired = quantity if replace else current + quantity
        final = max(1, min(desired, product.stock))
        self._cart[pid] = final
        self._save()
        return final

    def remove(self, product: Product) -> None:
        pid = str(product.pk)
        if pid in self._cart:
            del self._cart[pid]
            self._save()

    def clear(self) -> None:
        self._cart = {}
        self._save()

    def __iter__(self) -> Iterator[CartLine]:
        products = Product.objects.filter(pk__in=self._cart.keys()).select_related("category")
        for product in products:
            yield CartLine(product, self._cart[str(product.pk)])

    def __len__(self) -> int:
        return sum(self._cart.values())

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self), Decimal("0"))

    @property
    def is_empty(self) -> bool:
        return not self._cart
