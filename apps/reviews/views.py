from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from apps.catalog.models import Product

from .forms import ReviewForm
from .services import can_review


class ReviewCreateView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        product = get_object_or_404(Product.objects.active(), slug=slug)
        if not can_review(request.user, product):
            messages.error(request, "Відгук можна залишити один раз і лише після покупки.")
            return redirect(product)

        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            messages.success(request, "Дякуємо за відгук!")
        else:
            messages.error(request, "Оберіть оцінку від 1 до 5.")
        return redirect(product)
