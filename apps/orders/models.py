from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, F, Sum

from apps.catalog.models import Product
from apps.core.models import TimeStampedModel
from apps.delivery.models import DeliveryType


class Order(TimeStampedModel):
    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Очікує оплати"
        PAID = "paid", "Оплачено"
        SHIPPED = "shipped", "Відправлено"
        DELIVERED = "delivered", "Доставлено"
        CANCELLED = "cancelled", "Скасовано"

    class PaymentMethod(models.TextChoices):
        CARD = "card", "Банківська картка"
        WALLET = "wallet", "Apple Pay / Google Pay"
        COD = "cod", "Оплата при отриманні"

    DeliveryType = DeliveryType

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="покупець",
    )
    status = models.CharField(
        "статус", choices=OrderStatus.choices, default=OrderStatus.PENDING, max_length=10
    )
    total_price = models.DecimalField("сума", max_digits=10, decimal_places=2, default=Decimal("0"))
    shipping_address = models.TextField("адреса доставки")

    # Contact details and delivery, as entered at checkout.
    last_name = models.CharField("прізвище", max_length=150, blank=True)
    first_name = models.CharField("ім'я", max_length=150, blank=True)
    middle_name = models.CharField("по батькові", max_length=150, blank=True)
    email = models.EmailField("email", blank=True)
    phone = models.CharField("телефон", max_length=32, blank=True)
    payment_method = models.CharField(
        "спосіб оплати", choices=PaymentMethod.choices, default=PaymentMethod.CARD, max_length=10
    )
    delivery_type = models.CharField(
        "спосіб доставки", choices=DeliveryType.choices, default=DeliveryType.BRANCH, max_length=10
    )
    np_city_ref = models.CharField("ref міста НП", max_length=36, blank=True)
    np_warehouse_ref = models.CharField("ref відділення НП", max_length=36, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "замовлення"
        verbose_name_plural = "замовлення"

    def __str__(self) -> str:
        return f"Замовлення №{self.pk}"

    @property
    def full_name(self) -> str:
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )

    @property
    def can_cancel(self) -> bool:
        """An order can be cancelled until it has been shipped."""
        return self.status in (self.OrderStatus.PENDING, self.OrderStatus.PAID)

    # TODO: override save() щоб розрахувати total_price з OrderItem[] +
    # def save(self, *args, **kwargs):
    #     # Спочатку зберігаємо саме замовлення, щоб у нього з'явився ID в базі (якщо це нове замовлення)
    #     is_new = self.pk is None
    #     super().save(*args, **kwargs)
    #
    #     # Якщо замовлення вже існувало або ми перераховуємо суму після додавання OrderItem
    #     if not is_new and self.items.exists():
    #         # Рахуємо суму всіх пов'язаних OrderItem через property total
    #         total = sum(item.total for item in self.items.all())
    #
    #         # Якщо порахована сума відрізняється від поточної total_price, оновлюємо її
    #         if self.total_price != total:
    #             self.total_price = total
    #             # Використовуємо update_fields, щоб уникнути нескінченної рекурсії при повторному save()
    #             super().save(update_fields=["total_price"])

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
        verbose_name="замовлення",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="товар",
    )
    quantity = models.PositiveIntegerField("кількість")
    price = models.DecimalField("ціна", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "позиція замовлення"
        verbose_name_plural = "позиції замовлення"

    def __str__(self) -> str:
        return f"{self.product} x {self.quantity}"

    @property
    def total(self) -> Decimal:
        # TODO: підрахунок загальної ціни цього продукту в замовленні +
        return Decimal(self.quantity) * self.price
