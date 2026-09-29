from django import forms

from apps.core.validators import normalize_phone
from apps.delivery.forms import DeliveryForm

from .models import Order


class CartQuantityForm(forms.Form):
    quantity = forms.IntegerField(min_value=0, max_value=99)


class CheckoutForm(DeliveryForm):
    last_name = forms.CharField(label="Прізвище", max_length=150)
    first_name = forms.CharField(label="Ім'я", max_length=150)
    middle_name = forms.CharField(label="По батькові", max_length=150, required=False)
    phone = forms.CharField(label="Телефон", max_length=32)
    payment_method = forms.ChoiceField(label="Спосіб оплати", choices=Order.PaymentMethod.choices)

    def clean_phone(self) -> str:
        return normalize_phone(self.cleaned_data["phone"])
