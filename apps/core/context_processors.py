from django.conf import settings
from django.http import HttpRequest

from apps.catalog.models import Category
from apps.orders.cart import Cart


def shop(request: HttpRequest) -> dict:
    """Спільні для всіх шаблонів дані: назва магазину, категорії, лічильник кошика."""
    return {
        "SHOP_NAME": settings.SHOP_NAME,
        "categories": Category.objects.filter(parent__isnull=True),
        "cart_count": len(Cart(request)),
    }
