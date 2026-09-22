from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["line_total"]

    @admin.display(description="Line total")
    def line_total(self, obj: OrderItem) -> str:
        return str(obj.line_total)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "payment_method", "total_price", "created_at"]
    list_filter = ["status", "payment_method", "created_at"]
    search_fields = ["id", "full_name", "email", "user__username"]
    date_hierarchy = "created_at"
    readonly_fields = ["total_price", "created_at", "updated_at"]
    inlines = [OrderItemInline]
    actions = ["mark_shipped", "mark_delivered"]

    @admin.action(description="Позначити як відправлені")
    def mark_shipped(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(status=Order.OrderStatus.SHIPPED)
        self.message_user(request, f"{updated} замовлень позначено відправленими.")

    @admin.action(description="Позначити як доставлені")
    def mark_delivered(self, request: HttpRequest, queryset: QuerySet) -> None:
        updated = queryset.update(status=Order.OrderStatus.DELIVERED)
        self.message_user(request, f"{updated} замовлень позначено доставленими.")
