from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.catalog.models import Product
from apps.orders.models import Order

# Статуси, що формують виторг (оплачені та далі по циклу).
REVENUE_STATUSES = (
    Order.OrderStatus.PAID,
    Order.OrderStatus.SHIPPED,
    Order.OrderStatus.DELIVERED,
)


def health(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"healthy": True})


@staff_member_required
def analytics(request: HttpRequest) -> HttpResponse:
    """Адмін-сторінка аналітики: виторг, замовлення, топ-товари, розбивки по статусу і днях."""
    paid = Order.objects.filter(status__in=REVENUE_STATUSES)
    agg = paid.aggregate(
        revenue=Sum("total_price"),
        orders_count=Count("id"),
        average_check=Avg("total_price"),
    )
    summary = {
        "revenue": agg["revenue"] or 0,
        "orders_count": agg["orders_count"] or 0,
        "average_check": agg["average_check"] or 0,
    }

    top_products = Product.objects.with_sold().order_by("-sold_qty")[:10]

    status_counts = {
        row["status"]: row["count"]
        for row in Order.objects.values("status").annotate(count=Count("id"))
    }
    by_status = [
        {"label": label, "count": status_counts.get(value, 0)}
        for value, label in Order.OrderStatus.choices
    ]

    by_day = [
        {"day": row["day"], "orders": row["orders"], "revenue": row["revenue"] or 0}
        for row in (
            Order.objects.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(orders=Count("id"), revenue=Sum("total_price"))
            .order_by("-day")[:14]
        )
    ]

    return render(
        request,
        "admin/analytics.html",
        {
            "summary": summary,
            "top_products": top_products,
            "by_status": by_status,
            "by_day": by_day,
            "site_title": "Hop & Barley admin",
        },
    )
