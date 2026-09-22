from django.db import transaction

from apps.catalog.models import Product

from .cart import Cart
from .models import Order, OrderItem


class OutOfStock(Exception):
    """Товару не вистачає на складі під час оформлення замовлення."""

    def __init__(self, product: Product) -> None:
        self.product = product
        super().__init__(f"Not enough stock for {product}")


@transaction.atomic
def create_order_from_cart(
    user,
    cart: Cart,
    *,
    full_name: str,
    email: str,
    phone: str,
    shipping_address: str,
    payment_method: str,
) -> Order:
    """Створює замовлення з кошика в одній транзакції.

    Блокує товари (select_for_update), перевіряє і списує залишки, фіксує ціну на момент
    покупки. Кидає OutOfStock, якщо залишку не вистачає (транзакція відкочується).
    """
    lines = list(cart)
    if not lines:
        raise ValueError("Cart is empty")

    locked = {
        product.pk: product
        for product in Product.objects.select_for_update().filter(
            pk__in=[line.product.pk for line in lines]
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

    for line in lines:
        product = locked[line.product.pk]
        if line.quantity > product.stock:
            raise OutOfStock(product)
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=line.quantity,
            price=product.price,
        )
        product.stock -= line.quantity
        product.save(update_fields=["stock", "updated_at"])

    order.recalculate_total()
    return order
