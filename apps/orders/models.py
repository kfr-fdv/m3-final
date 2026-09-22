from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, F, Sum
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Credit / Debit Card"
        CASH = "cash", "Cash on Delivery"

    # Статуси, за яких замовлення ще можна скасувати.
    CANCELLABLE_STATUSES = {OrderStatus.PENDING, OrderStatus.PAID}

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        choices=OrderStatus.choices, default=OrderStatus.PENDING, max_length=10
    )
    payment_method = models.CharField(
        choices=PaymentMethod.choices, default=PaymentMethod.CARD, max_length=10
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    # Контактні дані отримувача — знімок на момент оформлення замовлення.
    full_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    shipping_address = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.pk}"

    def get_absolute_url(self) -> str:
        return reverse("orders:order_detail", kwargs={"pk": self.pk})

    @property
    def can_cancel(self) -> bool:
        """Чи можна скасувати замовлення у поточному статусі."""
        return self.status in self.CANCELLABLE_STATUSES

    def recalculate_total(self) -> Decimal:
        """Recalculate total_price from the current order items."""
        result = self.items.aggregate(
            total=Sum(
                F("price") * F("quantity"),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        )
        self.total_price = result["total"] or Decimal("0")
        self.save(update_fields=["total_price", "updated_at"])
        return self.total_price


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"

    @property
    def line_total(self) -> Decimal:
        """Загальна вартість цієї позиції замовлення (ціна × кількість)."""
        return Decimal(self.quantity) * self.price
