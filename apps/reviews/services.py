from django.contrib.auth.models import AnonymousUser

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.orders.models import Order

from .models import Review

PURCHASED_STATUSES = (
    Order.OrderStatus.PAID,
    Order.OrderStatus.SHIPPED,
    Order.OrderStatus.DELIVERED,
)


def can_review(user: User | AnonymousUser, product: Product) -> bool:
    """A user may review a product once, and only after buying it."""
    if not user.is_authenticated:
        return False
    bought = Order.objects.filter(
        user_id=user.pk, status__in=PURCHASED_STATUSES, items__product=product
    ).exists()
    already_reviewed = Review.objects.filter(user_id=user.pk, product=product).exists()
    return bought and not already_reviewed
