from django.urls import path

from .views import (
    DashboardView,
    ProductCreateView,
    ProductDeleteView,
    ProductListView,
    ProductToggleView,
    ProductUpdateView,
)

app_name = "staff"

urlpatterns = [
    path("products/", ProductListView.as_view(), name="products"),
    path("products/add/", ProductCreateView.as_view(), name="product_add"),
    path("products/<int:pk>/", ProductUpdateView.as_view(), name="product_edit"),
    path("products/<int:pk>/toggle/", ProductToggleView.as_view(), name="product_toggle"),
    path("products/<int:pk>/delete/", ProductDeleteView.as_view(), name="product_delete"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]
