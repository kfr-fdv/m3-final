from typing import Any

from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.core.validators import normalize_phone
from apps.delivery.forms import DeliveryForm

from .models import User


class RegisterForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    remember_me = forms.BooleanField(label="Запам'ятати мене", required=False, initial=True)

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Акаунт з таким email уже існує.")
        return email

    def clean_password(self) -> str:
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def save(self) -> User:
        email = self.cleaned_data["email"]
        return User.objects.create_user(
            username=email, email=email, password=self.cleaned_data["password"]
        )


class ProfileForm(DeliveryForm, forms.ModelForm):
    """Personal info + the saved Nova Poshta delivery point (optional here)."""

    delivery_required = False

    class Meta:
        model = User
        fields = ("last_name", "first_name", "middle_name", "phone", "email")
        labels = {"last_name": "Прізвище", "first_name": "Ім'я", "email": "Email"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        instance = kwargs.get("instance")
        if instance is not None:
            kwargs["initial"] = instance.delivery_initial() | kwargs.get("initial", {})
        super().__init__(*args, **kwargs)
        self.fields["last_name"].required = True
        self.fields["first_name"].required = True

    def clean_phone(self) -> str:
        phone = self.cleaned_data["phone"]
        return normalize_phone(phone) if phone else ""

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        data = self.cleaned_data
        user.remember_delivery(data.get("city_name", ""), data["delivery_type"], data["warehouse"])
        if commit:
            user.save()
        return user
