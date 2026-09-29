"""A small client for the Nova Poshta API 2.0: city and branch search for the checkout.

Every call is `POST <api url>` with `modelName` + `calledMethod` in the JSON body.
The API answers HTTP 200 even on errors, so we check the `success` flag instead.
"""

from dataclasses import dataclass
from typing import Any

import requests  # noqa: F401  # used in call(), written at K5
from django.conf import settings

POSTOMAT_TYPE_REF = "f9316480-5f2d-425d-bc2c-ac7cd29decf0"  # Address/getWarehouseTypes
NOTHING_FOUND = "FindByString is not specified"


class NovaPoshtaError(Exception):
    """The API is unreachable or rejected the request."""


@dataclass(frozen=True)
class City:
    ref: str
    name: str
    area: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.area} обл.)" if self.area else self.name


@dataclass(frozen=True)
class Warehouse:
    ref: str
    city_ref: str
    city_name: str
    number: str
    name: str
    is_postomat: bool


class NovaPoshtaClient:
    def __init__(self, api_key: str, api_url: str, timeout: float = 5) -> None:
        self.api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    def call(self, model: str, method: str, **properties: Any) -> list[dict[str, Any]]:
        """Call one API method and return its `data` list."""
        if not self.api_key:
            raise NovaPoshtaError("NOVA_POSHTA_API_KEY не налаштований.")
        payload = {
            "apiKey": self.api_key,
            "modelName": model,
            "calledMethod": method,
            "methodProperties": properties
        }
        try:
            response = requests.post(self.api_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as error:
            raise NovaPoshtaError(f"API Нової Пошти недоступне: {error}") from error

        if not body.get("success"):
            raise NovaPoshtaError("; ".join(body.get("errors") or ["Невідома помилка API."]))
        return body["data"]

    def search_cities(self, query: str, limit: int = 10) -> list[City]:
        """Cities by substring; an empty query or nothing found gives an empty list."""
        try:
            result = self.call(
                "Address",
                "getCities",
                FindByString=query,
                Limit=str(limit),
            )
        except NovaPoshtaError as error:
            if NOTHING_FOUND in str(error):
                return []
            raise

        try:
            return [
                City(
                    ref=address["Ref"],
                    name=address["Description"],
                    area=address["AreaDescription"],
                )
                for address in result
            ]
        except KeyError:
            return []


    def search_warehouses(
        self, city_ref: str, query: str = "", postomat: bool = False, limit: int = 20
    ) -> list[Warehouse]:
        """Branches or parcel lockers of one city."""
        properties = {"CityRef": city_ref, "FindByString": query}
        if postomat:
            properties |= {"TypeOfWarehouseRef": POSTOMAT_TYPE_REF, "Limit": str(limit)}
        else:
            properties |= {"Limit": "100"}
        warehouses = [
            self._warehouse(row) for row in self.call("Address", "getWarehouses", **properties)
        ]
        return [w for w in warehouses if w.is_postomat == postomat][:limit]

    def get_warehouse(self, ref: str) -> Warehouse | None:
        rows = self.call("Address", "getWarehouses", Ref=ref)
        return self._warehouse(rows[0]) if rows else None

    @staticmethod
    def _warehouse(row: dict[str, Any]) -> Warehouse:
        return Warehouse(
            ref=row["Ref"],
            city_ref=row["CityRef"],
            city_name=row.get("CityDescription", ""),
            number=row.get("Number", ""),
            name=row["Description"],
            is_postomat=row.get("CategoryOfWarehouse") == "Postomat",
        )


def get_client() -> NovaPoshtaClient:
    return NovaPoshtaClient(settings.NOVA_POSHTA_API_KEY, settings.NOVA_POSHTA_API_URL)
