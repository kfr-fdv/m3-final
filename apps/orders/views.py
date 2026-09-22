from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.catalog.models import Product

from .cart import Cart
from .forms import CartAddForm


class CartView(TemplateView):
    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs: object) -> dict:
        context = super().get_context_data(**kwargs)
        cart = Cart(self.request)
        context["lines"] = list(cart)
        context["total"] = cart.total
        context["is_empty"] = cart.is_empty
        return context


class CartAddView(View):
    def post(self, request: HttpRequest, product_id: int) -> HttpResponse:
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        form = CartAddForm(request.POST)
        quantity = form.cleaned_data["quantity"] if form.is_valid() else 1
        final = Cart(request).add(product, quantity)
        if final == 0:
            messages.error(request, f"«{product.name}» зараз немає в наявності.")
        else:
            messages.success(request, f"«{product.name}» додано до кошика.")
        return redirect("orders:cart")


class CartUpdateView(View):
    def post(self, request: HttpRequest, product_id: int) -> HttpResponse:
        product = get_object_or_404(Product, pk=product_id, is_active=True)
        cart = Cart(request)
        form = CartAddForm(request.POST)
        if not form.is_valid():
            cart.remove(product)
            messages.info(request, f"«{product.name}» видалено з кошика.")
        else:
            final = cart.add(product, form.cleaned_data["quantity"], replace=True)
            if final < form.cleaned_data["quantity"]:
                messages.warning(request, f"Доступно лише {product.stock} шт. «{product.name}».")
            else:
                messages.success(request, "Кошик оновлено.")
        return redirect("orders:cart")


class CartRemoveView(View):
    def post(self, request: HttpRequest, product_id: int) -> HttpResponse:
        product = get_object_or_404(Product, pk=product_id)
        Cart(request).remove(product)
        messages.info(request, f"«{product.name}» видалено з кошика.")
        return redirect("orders:cart")


class CheckoutView(TemplateView): ...


class OrderListView(TemplateView): ...


class OrderDetailView(TemplateView): ...


class OrderCancelView(TemplateView): ...
