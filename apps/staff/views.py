from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.orders.models import Order

from .forms import ProductForm


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only staff members manage the shop; everyone else gets 403."""

    request: HttpRequest

    def test_func(self) -> bool:
        return self.request.user.is_staff


# --- Product management -------------------------------------------------------------


class ProductListView(StaffRequiredMixin, ListView):
    template_name = "staff/products.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self) -> QuerySet[Product]:
        # Hidden products too: staff must be able to find and show them again.
        return Product.objects.select_related("category").order_by("-created_at", "-pk")


class ProductCreateView(StaffRequiredMixin, SuccessMessageMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "staff/product_form.html"
    success_message = "Товар створено."

    def get_success_url(self) -> str:
        assert self.object is not None  # set by form_valid()
        return reverse("staff:product_edit", kwargs={"pk": self.object.pk})


class ProductUpdateView(StaffRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "staff/product_form.html"
    success_message = "Зміни збережено."

    def get_success_url(self) -> str:
        return reverse("staff:product_edit", kwargs={"pk": self.object.pk})


class ProductToggleView(StaffRequiredMixin, View):
    """The "Hide" button: a hidden product disappears from the catalog but keeps its orders."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save(update_fields=["is_active", "updated_at"])
        messages.success(
            request, "Товар знову в каталозі." if product.is_active else "Товар приховано."
        )
        return redirect("staff:product_edit", pk=pk)


class ProductDeleteView(StaffRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        product = get_object_or_404(Product, pk=pk)
        try:
            product.delete()
        except ProtectedError:
            messages.error(
                request, "Товар є в замовленнях, тому його не можна видалити. Приховайте його."
            )
            return redirect("staff:product_edit", pk=pk)
        messages.success(request, f"«{product.name}» видалено.")
        return redirect("staff:products")


# --- Dashboard ----------------------------------------------------------------------

PERIODS = {
    "today": ("Сьогодні", 1, "учорашнім днем"),
    "week": ("7 днів", 7, "попереднім тижнем"),
    "month": ("30 днів", 30, "попереднім місяцем"),
    "all": ("Увесь час", None, ""),
}


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "staff/dashboard.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get("period", "today")
        if period not in PERIODS:
            period = "today"
        _, days, compared_to = PERIODS[period]

        now = timezone.now()
        if days is None:
            current, previous = self.stats(None, now), None
        else:
            start = now - timedelta(days=days)
            current = self.stats(start, now)
            previous = self.stats(start - timedelta(days=days), start)

        context["periods"] = [(key, label) for key, (label, _, _) in PERIODS.items()]
        context["period"] = period
        context["cards"] = [
            self.card("Продажі", "sales", current, previous, compared_to),
            self.card("Користувачі", "users", current, previous, compared_to),
            self.card("Замовлення", "orders", current, previous, compared_to),
            self.card("Очікують оплати", "pending", current, previous, compared_to),
        ]
        return context

    @staticmethod
    def stats(start: Any, end: Any) -> dict[str, Decimal | int]:
        """Numbers for orders and sign-ups created in [start, end); start=None means all time."""
        orders = Order.objects.filter(created_at__lt=end)
        users = User.objects.filter(date_joined__lt=end)
        if start is not None:
            orders = orders.filter(created_at__gte=start)
            users = users.filter(date_joined__gte=start)
        sales = orders.exclude(status=Order.OrderStatus.CANCELLED).aggregate(
            total=Sum("total_price")
        )["total"]
        return {
            "sales": sales or Decimal("0"),
            "users": users.count(),
            "orders": orders.count(),
            "pending": orders.filter(status=Order.OrderStatus.PENDING).count(),
        }

    @staticmethod
    def card(
        title: str,
        key: str,
        current: dict[str, Decimal | int],
        previous: dict[str, Decimal | int] | None,
        compared_to: str,
    ) -> dict[str, Any]:
        card: dict[str, Any] = {"title": title, "key": key, "value": current[key], "delta": None}
        if previous is not None and previous[key]:
            change = (Decimal(current[key]) - Decimal(previous[key])) / Decimal(previous[key]) * 100
            card["delta"] = {"percent": abs(change), "up": change >= 0, "compared_to": compared_to}
        return card
