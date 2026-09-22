import django_filters as filters
from django.db.models import Q

from .models import Category, Product


class ProductFilter(filters.FilterSet):
    """Filters for the product list. The same class will later serve the API."""

    search = filters.CharFilter(method="filter_search", label="Search")
    category = filters.CharFilter(method="filter_category", label="Category")
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")
    in_stock = filters.BooleanFilter(method="filter_in_stock", label="In stock only")
    ordering = filters.OrderingFilter(
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
        """K4-G1: пошук за назвою та описом товару."""
        return queryset.filter(self._search_query(value))

    def filter_category(self, queryset, name, value):
        """K4-G2: фільтр за slug категорії разом з усіма її підкатегоріями."""
        category = Category.objects.filter(slug=value).first()
        if category is None:
            return queryset
        return queryset.filter(category_id__in=self._descendant_ids(category))

    def filter_in_stock(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(stock__gt=0)

    @staticmethod
    def _search_query(value: str) -> Q:
        return Q(name__icontains=value) | Q(description__icontains=value)

    @staticmethod
    def _descendant_ids(category: Category) -> list[int]:
        """Id категорії та всіх її нащадків (довільна глибина вкладеності)."""
        ids = [category.pk]
        frontier = [category.pk]
        while frontier:
            children = list(
                Category.objects.filter(parent_id__in=frontier).values_list("pk", flat=True)
            )
            ids.extend(children)
            frontier = children
        return ids
