from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegisterForm(UserCreationForm):
    """Реєстрація користувача з обов'язковим email."""

    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class ProfileForm(forms.ModelForm):
    """Редагування особистих даних у кабінеті."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "default_address")
