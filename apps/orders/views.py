from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.accounts.models import User
from apps.catalog.models import Product

from .cart import Cart, NotEnoughStock
from .forms import CartQuantityForm, CheckoutForm
from .models import Order
from .services import CheckoutError, create_order


class CartView(TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        cart = Cart(self.request.session)
        lines = list(cart)
        context.update(
            lines=lines,
            total=sum((line.line_total for line in lines), 0),
            is_empty=not lines,
        )
        return context


class CartChangeView(View):
    """Base for the POST-only cart actions: loads the product and the cart."""

    http_method_names = ["post"]

    def post(self, request: HttpRequest, product_id: int) -> HttpResponse:
        product = get_object_or_404(Product.objects.active(), pk=product_id)
        cart = Cart(request.session)
        try:
            return self.change(cart, product)
        except NotEnoughStock as error:
            messages.error(request, str(error))
            return redirect(self.back_url(product))

    def change(self, cart: Cart, product: Product) -> HttpResponse:
        raise NotImplementedError

    def back_url(self, product: Product) -> str:
        return reverse("orders:cart")

    def quantity(self, default: int) -> int:
        form = CartQuantityForm(self.request.POST or None)
        return form.cleaned_data["quantity"] if form.is_valid() else default


class CartAddView(CartChangeView):
    def change(self, cart: Cart, product: Product) -> HttpResponse:
        cart.add(product, max(self.quantity(default=1), 1))
        messages.success(self.request, f"«{product.name}» додано до кошика.")
        return redirect(self.back_url(product))

    def back_url(self, product: Product) -> str:
        return product.get_absolute_url()


class CartUpdateView(CartChangeView):
    def change(self, cart: Cart, product: Product) -> HttpResponse:
        cart.update(product, self.quantity(default=0))
        return redirect("orders:cart")


class CartRemoveView(CartChangeView):
    def change(self, cart: Cart, product: Product) -> HttpResponse:
        cart.remove(product)
        messages.info(self.request, f"«{product.name}» прибрано з кошика.")
        return redirect("orders:cart")


class CheckoutView(LoginRequiredMixin, FormView):
    template_name = "orders/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if request.user.is_authenticated and not Cart(request.session).items:
            messages.info(request, "Кошик порожній.")
            return redirect("orders:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self) -> dict[str, Any]:
        user: User = self.request.user  # type: ignore[assignment]  # LoginRequiredMixin
        return {
            "last_name": user.last_name,
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "phone": user.phone,
            "payment_method": Order.PaymentMethod.CARD,
            **user.delivery_initial(),  # saved in the account or by the previous order
        }

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        lines = list(Cart(self.request.session))
        context.update(
            lines=lines,
            items_count=sum(line.quantity for line in lines),
            total=sum((line.line_total for line in lines), 0),
        )
        return context

    def form_valid(self, form: CheckoutForm) -> HttpResponse:
        cart = Cart(self.request.session)
        try:
            order = create_order(self.request.user, cart, form.cleaned_data)  # type: ignore[arg-type]
        except CheckoutError as error:
            messages.error(self.request, str(error))
            return redirect("orders:cart")
        cart.clear()
        messages.success(self.request, f"Дякуємо! Замовлення №{order.pk} оформлено.")
        return redirect(reverse("accounts:profile"))
