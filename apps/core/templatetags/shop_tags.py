from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.template import Library
from django.utils.html import format_html_join
from django.utils.safestring import SafeString

register = Library()


# 300|money > $300
@register.filter
def money(value: Decimal | float | str | None) -> str:
    if value is None:
        return ""
    try:
        amount = Decimal(value)
    except (ValueError, InvalidOperation):
        return ""
    return f"{settings.SHOP_CURRENCY}{amount:.2f}"


# {% stars product.avg_rating %}
@register.simple_tag
def stars(rating: float) -> SafeString:
    filled = round(rating or 0)
    return format_html_join(
        "",
        '<span class="star{}">{}</span>',
        ((" star--filled", "★") if number <= filled else ("", "☆") for number in range(1, 6)),
    )


RATING_LABELS = {1: "Погано", 2: "Так собі", 3: "Добре", 4: "Дуже добре", 5: "Чудово"}


# {{ review.rating|rating_label }} -> "Чудово"
@register.filter
def rating_label(rating: int | None) -> str:
    return RATING_LABELS.get(rating or 0, "")
