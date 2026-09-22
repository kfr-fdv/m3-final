# Create your views here.
from django.views.generic import DetailView, ListView, TemplateView

from .filters import ProductFilter
from .models import Category, Product


class HomeView(TemplateView):
    template_name = "catalog/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["featured_products"] = Product.objects.for_listing()[:8]
        context["categories"] = Category.objects.filter(parent__isnull=True)
        return context


class ProductDetailView(DetailView):
    template_name = "catalog/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.for_listing()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        context["reviews"] = product.reviews.select_related("user")
        context["related_products"] = (
            Product.objects.for_listing().filter(category=product.category).exclude(pk=product.pk)
        )

        return context


class ProductListView(ListView):
    template_name = "catalog/product_list.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        self.filter = ProductFilter(self.request.GET, queryset=Product.objects.for_listing())
        return self.filter.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["filter"] = self.filter
        context["categories"] = Category.objects.filter(parent__isnull=True)

        return context
