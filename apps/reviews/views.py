from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.catalog.models import Product

from .forms import ReviewForm
from .services import user_can_review


class ReviewCreateView(LoginRequiredMixin, View):
    """Створення відгуку — лише після покупки товару і не повторно."""

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        product = get_object_or_404(Product, slug=slug, is_active=True)
        if not user_can_review(request.user, product):
            messages.error(request, "Залишити відгук можна лише після покупки товару.")
            return redirect(product.get_absolute_url())
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Дякуємо за відгук!")
        else:
            messages.error(request, "Не вдалося зберегти відгук. Перевірте форму.")
        return redirect(product.get_absolute_url())
