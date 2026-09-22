from apps.catalog.models import Product
from apps.orders.models import Order

# Статуси, за яких покупка вважається здійсненою (можна залишати відгук).
PURCHASED_STATUSES = (
    Order.OrderStatus.PAID,
    Order.OrderStatus.SHIPPED,
    Order.OrderStatus.DELIVERED,
)


def user_can_review(user, product: Product) -> bool:
    """Чи може користувач залишити відгук: лише після покупки і не повторно."""
    if not user.is_authenticated:
        return False
    if product.reviews.filter(user=user).exists():
        return False
    return Order.objects.filter(
        user=user,
        status__in=PURCHASED_STATUSES,
        items__product=product,
    ).exists()
