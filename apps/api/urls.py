from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from .views import (
    CartAPIView,
    LoginView,
    OrderViewSet,
    ProductReviewsView,
    ProductViewSet,
    RefreshTokenView,
    RegisterView,
    ReviewUpdateView,
)

app_name = "api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("users/register/", RegisterView.as_view(), name="register"),
    path("users/login/", LoginView.as_view(), name="login"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token_refresh"),
    path("cart/", CartAPIView.as_view(), name="cart"),
    path(
        "products/<int:product_id>/reviews/",
        ProductReviewsView.as_view(),
        name="product-reviews",
    ),
    path("reviews/<int:pk>/", ReviewUpdateView.as_view(), name="review-detail"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="docs"),
    *router.urls,
]
