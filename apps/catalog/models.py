from django.db import models
from django.db.models import Avg, Count, FloatField, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField("назва", max_length=100)
    slug = models.SlugField(max_length=300, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="батьківська категорія",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "категорія"
        verbose_name_plural = "категорії"

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return f"{reverse('catalog:product_list')}?category={self.slug}"


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def with_rating(self):
        return self.annotate(
            rating_avg=Coalesce(Avg("reviews__rating"), 0.0, output_field=FloatField()),
            rating_count=Count("reviews", distinct=True),
        )

    def with_sold(self):
        from apps.orders.models import Order, OrderItem

        sold = (
            OrderItem.objects.filter(product=OuterRef("pk"))
            .exclude(order__status=Order.OrderStatus.CANCELLED)
            .values("product")
            .annotate(total=Sum("quantity"))
            .values("total")
        )
        return self.annotate(
            sold_qty=Coalesce(Subquery(sold, output_field=IntegerField()), 0),
        )

    def for_listing(self):
        return (
            self.active()
            .select_related("category")
            .with_rating()
            .with_sold()
            .order_by("-created_at")
        )


class Product(TimeStampedModel):
    name = models.CharField("назва", max_length=100)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    description = models.TextField("опис", blank=True)
    price = models.DecimalField("ціна", max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name="категорія"
    )
    image = models.ImageField("фото", upload_to="products/", blank=True)
    is_active = models.BooleanField("показувати в каталозі", default=True)
    stock = models.PositiveIntegerField("залишок на складі", default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "товар"
        verbose_name_plural = "товари"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def in_stock(self) -> bool:
        return self.stock > 0
