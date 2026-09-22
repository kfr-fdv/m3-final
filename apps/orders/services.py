from collections.abc import Sequence

from django.db import transaction
from django.db.models import F

from apps.catalog.models import Product

from .cart import Cart
from .models import Order, OrderItem


class OutOfStock(Exception):
    """Товару не вистачає на складі під час оформлення замовлення."""

    def __init__(self, product: Product) -> None:
        self.product = product
        super().__init__(f"Not enough stock for {product}")


@transaction.atomic
def create_order(
    user,
    items: Sequence[tuple[int, int]],
    *,
    full_name: str,
    email: str,
    phone: str,
    shipping_address: str,
    payment_method: str,
) -> Order:
    """Створює замовлення зі списку позицій (product_id, quantity) в одній транзакції.

    Блокує товари (select_for_update), перевіряє і списує залишки, фіксує ціну на момент
    покупки. Кидає OutOfStock, якщо залишку не вистачає (транзакція відкочується).
    """
    if not items:
        raise ValueError("No items to order")

    locked = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(
            pk__in=[product_id for product_id, _ in items]
        )
    }

    order = Order.objects.create(
        user=user,
        full_name=full_name,
        email=email,
        phone=phone,
        shipping_address=shipping_address,
        payment_method=payment_method,
        status=Order.OrderStatus.PENDING,
    )

    for product_id, quantity in items:
        product = locked[product_id]
        if quantity > product.stock:
            raise OutOfStock(product)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            price=product.price,
        )
        product.stock -= quantity
        product.save(update_fields=["stock", "updated_at"])

    order.recalculate_total()
    return order


def create_order_from_cart(user, cart: Cart, **contact: str) -> Order:
    """Створює замовлення з вмісту session-кошика (обгортка над create_order)."""
    items = [(line.product.pk, line.quantity) for line in cart]
    return create_order(user, items, **contact)


@transaction.atomic
def cancel_order(order: Order) -> bool:
    """Скасовує замовлення і повертає товари на склад. False, якщо скасувати не можна."""
    if not order.can_cancel:
        return False
    for item in order.items.all():
        Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
    order.status = Order.OrderStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    return True
