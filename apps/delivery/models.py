from django.db import models


class DeliveryType(models.TextChoices):
    BRANCH = "branch", "Відділення Нової Пошти"
    POSTOMAT = "postomat", "Поштомат Нової Пошти"
