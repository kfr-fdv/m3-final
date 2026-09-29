from typing import Any

from django.db.models import QuerySet
from django.views.generic import DetailView, ListView

from apps.reviews.forms import ReviewForm
from apps.reviews.services import can_review

from .filters import ProductFilter
from .models import Category, Product


class ProductListView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self) -> QuerySet[Product]:
        self.filter = ProductFilter(self.request.GET, queryset=Product.objects.for_listing())
        return self.filter.qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["filter"] = self.filter
        context["categories"] = Category.objects.filter(parent__isnull=True)
        context["selected_categories"] = self.request.GET.getlist("category")
        context["active_keywords"] = self.active_keywords(context["categories"])
        return context

    def active_keywords(self, categories: QuerySet[Category]) -> list[dict[str, str]]:
        """Chips for the "Keywords" block: every active filter with a link that removes it."""
        params = self.request.GET.copy()
        params.pop("page", None)
        names = {category.slug: category.name for category in categories}
        keywords = []
        for slug in params.getlist("category"):
            rest = params.copy()
            rest.setlist(
                "category", [value for value in params.getlist("category") if value != slug]
            )
            keywords.append(
                {"label": names.get(slug, str(slug)), "remove_url": f"?{rest.urlencode()}"}
            )
        if params.get("search"):
            rest = params.copy()
            rest.pop("search")
            keywords.append(
                {"label": str(params.get("search")), "remove_url": f"?{rest.urlencode()}"}
            )
        return keywords


class HomeView(ProductListView):
    """The home page is the catalog itself, exactly as in the design mockup."""


class ProductDetailView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self) -> QuerySet[Product]:
        return Product.objects.for_listing()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        product = self.object
        context["reviews"] = product.reviews.select_related("user")
        context["can_review"] = can_review(self.request.user, product)
        context["review_form"] = ReviewForm()
        return context
