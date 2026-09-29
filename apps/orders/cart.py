"""Shopping cart stored in the session: {"<product id>": quantity}."""

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal

from django.contrib.sessions.backends.base import SessionBase

from apps.catalog.models import Product

CART_SESSION_KEY = "cart"


class NotEnoughStock(Exception):
    def __init__(self, product: Product) -> None:
        super().__init__(f"На жаль, «{product.name}» лишилось лише {product.stock} шт.")
        self.product = product


@dataclass
class CartLine:
    product: Product
    quantity: int

    @property
    def line_total(self) -> Decimal:
        return self.product.price * self.quantity


class Cart:
    def __init__(self, session: SessionBase) -> None:
        self.session = session
        self.items: dict[str, int] = session.setdefault(CART_SESSION_KEY, {})

    def add(self, product: Product, quantity: int = 1) -> None:
        self.update(product, self.items.get(str(product.pk), 0) + quantity)

    def update(self, product: Product, quantity: int) -> None:
        """Set the quantity of a product; zero removes it."""

        if quantity <= 0:
            self.remove(product)
            return
        if quantity > product.stock:
            raise NotEnoughStock(product)

        self.items[str(product.pk)] = quantity
        self.session.modified = True

    def remove(self, product: Product) -> None:
        self.items.pop(str(product.pk), None)
        self.session.modified = True

    def clear(self) -> None:
        self.items.clear()
        self.session.modified = True

    def __iter__(self) -> Iterator[CartLine]:
        """Lines with products loaded in one query; hidden or deleted products are skipped."""
        products = Product.objects.active().in_bulk([int(pk) for pk in self.items])
        for pk, quantity in self.items.items():
            product = products.get(int(pk))
            if product is not None:
                yield CartLine(product, quantity)

    def __len__(self) -> int:
        """Number of items in the cart, for the header badge (no database query)."""
        return sum(self.items.values())

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self), Decimal("0"))
