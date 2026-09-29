from dataclasses import asdict

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views import View

from .novaposhta import NovaPoshtaError, get_client

# Cities and branches change rarely: keep search results for a day.
CACHE_SECONDS = 60 * 60 * 24
UNAVAILABLE = {"error": "Сервіс доставки недоступний. Спробуйте пізніше."}


class CitySearchView(View):
    """GET /delivery/cities/?q=Льв -> cities for the checkout autocomplete."""

    def get(self, request: HttpRequest) -> JsonResponse:
        query = request.GET.get("q", "").strip()
        if len(query) < 2:
            return JsonResponse({"results": []})
        try:
            cities = (
                cache.get_or_set(
                    f"np:cities:{query.lower()}",
                    lambda: get_client().search_cities(query),
                    CACHE_SECONDS,
                )
                or []
            )
        except NovaPoshtaError:
            return JsonResponse(UNAVAILABLE, status=503)
        return JsonResponse({"results": [asdict(city) | {"label": city.label} for city in cities]})


class WarehouseSearchView(View):
    """GET /delivery/warehouses/?city=<ref>&type=postomat&q=12 -> branches of one city."""

    def get(self, request: HttpRequest) -> JsonResponse:
        city_ref = request.GET.get("city", "").strip()
        if not city_ref:
            return JsonResponse({"results": []})
        query = request.GET.get("q", "").strip()
        postomat = request.GET.get("type") == "postomat"
        try:
            warehouses = (
                cache.get_or_set(
                    f"np:warehouses:{city_ref}:{postomat}:{query.lower()}",
                    lambda: get_client().search_warehouses(city_ref, query, postomat=postomat),
                    CACHE_SECONDS,
                )
                or []
            )
        except NovaPoshtaError:
            return JsonResponse(UNAVAILABLE, status=503)
        return JsonResponse({"results": [asdict(warehouse) for warehouse in warehouses]})
