from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Користувач магазину з додатковими контактними полями."""

    phone = models.CharField("телефон", max_length=32, blank=True)
    default_address = models.TextField("адреса доставки за замовчуванням", blank=True)
