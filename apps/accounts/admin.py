from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class ShopUserAdmin(UserAdmin):
    fieldsets = (
        *(UserAdmin.fieldsets or ()),
        ("Контакти", {"fields": ("middle_name", "phone")}),
        ("Доставка Новою Поштою", {"fields": User.DELIVERY_FIELDS}),
    )
