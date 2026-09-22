from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.models import User
from apps.catalog.models import Product

from .cart import Cart
from .emails import send_order_created_emails
from .forms import CartAddForm, CheckoutForm
from .models import Order
from .services import OutOfStock, cancel_order, create_order_from_cart


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


class CheckoutView(LoginRequiredMixin, View):
    template_name = "orders/checkout.html"

    def _render(self, request: HttpRequest, form: CheckoutForm) -> HttpResponse:
        cart = Cart(request)
        return render(
            request,
            self.template_name,
            {"form": form, "lines": list(cart), "total": cart.total},
        )

    def get(self, request: HttpRequest) -> HttpResponse:
        if Cart(request).is_empty:
            messages.info(request, "Ваш кошик порожній.")
            return redirect("orders:cart")
        user = cast(User, request.user)
        form = CheckoutForm(
            initial={
                "full_name": user.get_full_name() or user.get_username(),
                "email": user.email,
                "phone": user.phone,
                "shipping_address": user.default_address,
            }
        )
        return self._render(request, form)

    def post(self, request: HttpRequest) -> HttpResponse:
        cart = Cart(request)
        if cart.is_empty:
            messages.info(request, "Ваш кошик порожній.")
            return redirect("orders:cart")
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return self._render(request, form)
        try:
            order = create_order_from_cart(request.user, cart, **form.cleaned_data)
        except OutOfStock as exc:
            messages.error(
                request,
                f"Недостатньо «{exc.product.name}» на складі. Оновіть кошик.",
            )
            return redirect("orders:cart")
        send_order_created_emails(order)
        cart.clear()
        messages.success(request, f"Замовлення #{order.pk} успішно оформлено.")
        return redirect(order.get_absolute_url())


class OrderListView(LoginRequiredMixin, ListView):
    template_name = "orders/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        self.current_status = self.request.GET.get("status") or ""
        orders = Order.objects.filter(user=self.request.user)
        if self.current_status:
            orders = orders.filter(status=self.current_status)
        return orders

    def get_context_data(self, **kwargs: Any) -> dict:
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.OrderStatus.choices
        context["current_status"] = self.current_status
        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")


class OrderCancelView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        order = get_object_or_404(Order, pk=pk, user=request.user)
        if cancel_order(order):
            messages.success(request, f"Замовлення #{order.pk} скасовано.")
        else:
            messages.error(request, "Це замовлення вже не можна скасувати.")
        return redirect(order.get_absolute_url())
