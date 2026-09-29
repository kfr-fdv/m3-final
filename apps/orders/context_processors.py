from django.http import HttpRequest

from .cart import Cart


def cart(request: HttpRequest) -> dict[str, int]:
    """Number of items for the cart badge in the header."""
    return {"cart_count": len(Cart(request.session))}
