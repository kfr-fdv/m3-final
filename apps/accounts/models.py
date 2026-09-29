from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.delivery.models import DeliveryType
from apps.delivery.novaposhta import Warehouse


class User(AbstractUser):
    middle_name = models.CharField("по батькові", max_length=150, blank=True)
    phone = models.CharField("телефон", max_length=32, blank=True)

    # Saved Nova Poshta delivery point. Refs are what the API needs; the names are kept
    # too, so pages show the address without asking the API every time.
    np_city_ref = models.CharField("ref міста НП", max_length=36, blank=True)
    np_city_name = models.CharField("місто", max_length=200, blank=True)
    np_delivery_type = models.CharField(
        "спосіб доставки", choices=DeliveryType.choices, default=DeliveryType.BRANCH, max_length=10
    )
    np_warehouse_ref = models.CharField("ref відділення НП", max_length=36, blank=True)
    np_warehouse_name = models.CharField("відділення", max_length=300, blank=True)

    def get_full_name(self) -> str:
        """Прізвище Ім'я По батькові, as usual in Ukraine."""
        return " ".join(
            part for part in (self.last_name, self.first_name, self.middle_name) if part
        )

    def delivery_initial(self) -> dict[str, Any]:
        """Saved delivery point as initial data for DeliveryForm fields."""
        return {
            "city_name": self.np_city_name,
            "city_ref": self.np_city_ref,
            "delivery_type": self.np_delivery_type,
            "warehouse_name": self.np_warehouse_name,
            "warehouse_ref": self.np_warehouse_ref,
        }

    def remember_delivery(
        self, city_name: str, delivery_type: str, warehouse: Warehouse | None
    ) -> None:
        """Store (or clear, when warehouse is None) the delivery point. Does not save()."""
        self.np_city_name = city_name if warehouse else ""
        self.np_city_ref = warehouse.city_ref if warehouse else ""
        self.np_delivery_type = delivery_type if warehouse else DeliveryType.BRANCH
        self.np_warehouse_ref = warehouse.ref if warehouse else ""
        self.np_warehouse_name = warehouse.name if warehouse else ""

    DELIVERY_FIELDS = (
        "np_city_ref",
        "np_city_name",
        "np_delivery_type",
        "np_warehouse_ref",
        "np_warehouse_name",
    )
