from django.db import models
from django.db.models import Avg, Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return f"{reverse('catalog:product_list')}?category={self.slug}"


class ProductQuerySet(models.QuerySet):
    def active(self):
        """Лише активні (доступні до продажу) товари."""
        return self.filter(is_active=True)

    def with_rating(self):
        """K4-G3: анотує rating_avg та rating_count за відгуками.

        Використовуємо підзапити замість агрегації по зв'язку, щоб уникнути
        множення рядків при одночасній анотації sold_qty (fan-out по JOIN).
        """
        from apps.reviews.models import Review

        reviews = Review.objects.filter(product=OuterRef("pk")).values("product")
        return self.annotate(
            rating_avg=Subquery(reviews.annotate(avg=Avg("rating")).values("avg")),
            rating_count=Coalesce(
                Subquery(
                    reviews.annotate(cnt=Count("id")).values("cnt"),
                    output_field=IntegerField(),
                ),
                0,
            ),
        )

    def with_sold(self):
        """K4-G4: анотує sold_qty — кількість уже замовлених одиниць.

        Рахуємо по позиціях у не скасованих замовленнях через підзапит.
        """
        from apps.orders.models import Order, OrderItem

        sold = (
            OrderItem.objects.filter(product=OuterRef("pk"))
            .exclude(order__status=Order.OrderStatus.CANCELLED)
            .values("product")
            .annotate(total=models.Sum("quantity"))
            .values("total")
        )
        return self.annotate(sold_qty=Coalesce(Subquery(sold, output_field=IntegerField()), 0))

    def for_listing(self):
        """Everything a product card needs: active, with category, rating and sales."""
        return (
            self.active()
            .select_related("category")
            .with_rating()
            .with_sold()
            .order_by("-created_at")
        )


class Product(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    image = models.ImageField(upload_to="products/", blank=True)
    is_active = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    # TODO: override save() і добавити автоматичний slug, якщо він пустий
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def in_stock(self) -> bool:
        return self.stock > 0
