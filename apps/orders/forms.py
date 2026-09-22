from django import forms

from .models import Order


class CheckoutForm(forms.ModelForm):
    """Контактні дані та спосіб оплати під час оформлення замовлення."""

    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        widget=forms.RadioSelect,
        initial=Order.PaymentMethod.CARD,
    )

    class Meta:
        model = Order
        fields = ("full_name", "email", "phone", "shipping_address", "payment_method")


class CartAddForm(forms.Form):
    """Кількість товару під час додавання в кошик."""

    quantity = forms.IntegerField(min_value=1, initial=1)
