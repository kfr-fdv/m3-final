from typing import Any

from django import forms

from .models import DeliveryType
from .novaposhta import NovaPoshtaError, get_client


class DeliveryForm(forms.Form):
    """Nova Poshta city + branch fields, shared by the checkout and the account page.

    The customer types the city and picks a branch from the suggestions; the page puts
    the refs of the picked items into hidden fields. clean() checks the branch with the
    API and puts it into cleaned_data["warehouse"] (None when the fields are left empty).
    """

    delivery_required = True

    city_name = forms.CharField(label="Місто", max_length=200)
    city_ref = forms.CharField(
        widget=forms.HiddenInput, error_messages={"required": "Оберіть місто зі списку."}
    )
    delivery_type = forms.ChoiceField(label="Спосіб доставки", choices=DeliveryType.choices)
    warehouse_name = forms.CharField(label="Відділення", max_length=300)
    warehouse_ref = forms.CharField(
        widget=forms.HiddenInput, error_messages={"required": "Оберіть відділення зі списку."}
    )

    DELIVERY_FIELDS = ("city_name", "city_ref", "delivery_type", "warehouse_name", "warehouse_ref")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.delivery_required:
            for name in self.DELIVERY_FIELDS:
                self.fields[name].required = False

    def clean(self) -> dict[str, Any]:
        """Never trust refs from the browser: ask Nova Poshta about the branch again."""
        super().clean()
        data = self.cleaned_data
        data["warehouse"] = None
        if self.errors:
            return data
        if not data.get("city_ref") and not data.get("warehouse_ref"):
            return data  # optional delivery left empty
        if not data.get("warehouse_ref"):
            self.add_error("warehouse_name", "Оберіть відділення зі списку.")
            return data
        try:
            warehouse = get_client().get_warehouse(data["warehouse_ref"])
        except NovaPoshtaError as error:
            raise forms.ValidationError(
                "Не вдалося перевірити відділення. Спробуйте ще раз за хвилину."
            ) from error

        wants_postomat = data["delivery_type"] == DeliveryType.POSTOMAT
        if warehouse is None or warehouse.city_ref != data["city_ref"]:
            self.add_error("warehouse_name", "Оберіть відділення у вибраному місті.")
        elif warehouse.is_postomat != wants_postomat:
            self.add_error("warehouse_name", "Відділення не відповідає способу доставки.")
        else:
            data["warehouse"] = warehouse
        return data
