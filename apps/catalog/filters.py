import django_filters as filters
from django.db.models import Q

from .models import Category, Product


class StableOrderingFilter(filters.OrderingFilter):
    def filter(self, qs, value):
        qs = super().filter(qs, value)
        if value:
            qs = qs.order_by(*qs.query.order_by, "-pk")
        return qs


class ProductFilter(filters.FilterSet):
    """Filters for the product list. The same class will later serve the API."""

    search = filters.CharFilter(method="filter_search", label="Пошук")
    category = filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.all(),
        to_field_name="slug",
        method="filter_category",
        label="Тип товару",
    )
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = filters.BooleanFilter(method="filter_in_stock", label="Лише в наявності")
    ordering = StableOrderingFilter(
        fields=(
            ("price", "price"),
            ("created_at", "created_at"),
            ("rating_avg", "rating"),
            ("sold_qty", "popularity"),
        ),
    )

    class Meta:
        model = Product
        fields: list[str] = []

    def filter_search(self, queryset, name, value):
        """Search in product name and description."""
        return queryset.filter(self._search_query(value))

    def filter_category(self, queryset, name, value):
        """Filter by one or more categories, including products of their subcategories."""
        if not value:
            return queryset
        return queryset.filter(Q(category__in=value) | Q(category__parent__in=value))

    def filter_in_stock(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(stock__gt=0)

    @staticmethod
    def _search_query(value: str) -> Q:
        return Q(name__icontains=value) | Q(description__icontains=value)
