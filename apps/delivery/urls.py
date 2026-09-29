from django.urls import path

from .views import CitySearchView, WarehouseSearchView

app_name = "delivery"

urlpatterns = [
    path("cities/", CitySearchView.as_view(), name="cities"),
    path("warehouses/", WarehouseSearchView.as_view(), name="warehouses"),
]
