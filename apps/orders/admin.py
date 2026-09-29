from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "payment_method", "total_price", "created_at"]
    list_filter = ["status", "payment_method", "delivery_type"]
    search_fields = ["id", "last_name", "first_name", "email", "phone"]
    inlines = [OrderItemInline]
