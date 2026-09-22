import shutil
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

User = get_user_model()

# (category_slug, category_name)
CATEGORIES = [
    ("hops", "Hops"),
    ("malt", "Malt"),
    ("yeast", "Yeast"),
    ("kits", "Kits"),
]

# (slug, name, category_slug, price, stock, image_file, description)
PRODUCTS = [
    (
        "citra-hops",
        "Citra Hops",
        "hops",
        "8.50",
        40,
        "citra_hops.jpg",
        "Citrus and tropical aroma hops.",
    ),
    (
        "cascade-hops",
        "Cascade Hops",
        "hops",
        "6.90",
        55,
        "cascade_hops.jpg",
        "Classic American floral hops.",
    ),
    (
        "mosaic-hops",
        "Mosaic Hops",
        "hops",
        "9.20",
        30,
        "mosaic_hops.jpg",
        "Complex berry and pine notes.",
    ),
    (
        "centennial-hops",
        "Centennial Hops",
        "hops",
        "7.40",
        45,
        "centennial_hops.jpg",
        "Balanced citrus bittering hops.",
    ),
    ("saaz-hops", "Saaz Hops", "hops", "7.10", 25, "saaz_hops.jpg", "Noble Czech aroma hops."),
    (
        "pilsner-malt",
        "Pilsner Malt",
        "malt",
        "2.30",
        200,
        "pilsner_malt.jpg",
        "Light base malt for lagers.",
    ),
    (
        "maris-otter-malt",
        "Maris Otter Malt",
        "malt",
        "2.80",
        180,
        "maris_otter_malt.jpg",
        "Premium British base malt.",
    ),
    (
        "caramel-malt",
        "Caramel Malt",
        "malt",
        "3.10",
        120,
        "caramel_malt.jpg",
        "Adds colour and sweetness.",
    ),
    (
        "unmalted-wheat",
        "Unmalted Wheat",
        "malt",
        "2.10",
        90,
        "unmalted_wheat.jpg",
        "For hazy wheat beers.",
    ),
    (
        "safale-us05-yeast",
        "SafAle US-05 Yeast",
        "yeast",
        "4.50",
        60,
        "safale_us05_yeast.jpg",
        "Clean American ale yeast.",
    ),
    (
        "imperial-yeast",
        "Imperial Yeast",
        "yeast",
        "9.90",
        20,
        "imperial_yeast.jpg",
        "Liquid yeast for big beers.",
    ),
    (
        "west-coast-ipa-kit",
        "West Coast IPA Kit",
        "kits",
        "39.00",
        15,
        "ipa_kit.jpg",
        "Everything for a hoppy IPA.",
    ),
]

REVIEWS = [
    ("citra-hops", 5, "Amazing aroma, my go-to hop."),
    ("citra-hops", 4, "Great but pricey."),
    ("pilsner-malt", 5, "Reliable base malt."),
    ("west-coast-ipa-kit", 5, "Brewed a fantastic IPA!"),
    ("safale-us05-yeast", 4, "Clean fermentation every time."),
]


class Command(BaseCommand):
    help = "Наповнює базу демонстраційними даними (ідемпотентно)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        categories = {
            slug: Category.objects.get_or_create(slug=slug, defaults={"name": name})[0]
            for slug, name in CATEGORIES
        }

        media_products = settings.MEDIA_ROOT / "products"
        media_products.mkdir(parents=True, exist_ok=True)
        static_products = settings.BASE_DIR / "static" / "img" / "products"

        products: dict[str, Product] = {}
        for slug, name, cat_slug, price, stock, image_file, description in PRODUCTS:
            source = static_products / image_file
            image_path = ""
            if source.exists():
                shutil.copy(source, media_products / image_file)
                image_path = f"products/{image_file}"
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "category": categories[cat_slug],
                    "price": Decimal(price),
                    "stock": stock,
                    "description": description,
                    "is_active": True,
                    "image": image_path,
                },
            )
            products[slug] = product

        demo, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@hopandbarley.local"},
        )
        if created:
            demo.set_password("demo12345")
            demo.phone = "+380000000000"
            demo.default_address = "1 Brew Street, Kyiv"
            demo.save()

        for slug, rating, comment in REVIEWS:
            Review.objects.get_or_create(
                user=demo,
                product=products[slug],
                defaults={"rating": rating, "comment": comment},
            )

        # Демо-замовлення (для аналітики) — лише якщо у користувача ще немає замовлень.
        if not Order.objects.filter(user=demo).exists():
            self._create_demo_order(
                demo,
                [(products["citra-hops"], 3), (products["pilsner-malt"], 5)],
                Order.OrderStatus.DELIVERED,
            )
            self._create_demo_order(
                demo,
                [(products["west-coast-ipa-kit"], 1)],
                Order.OrderStatus.PAID,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово: {len(categories)} категорій, {len(products)} товарів, "
                f"{Review.objects.count()} відгуків, {Order.objects.count()} замовлень."
            )
        )

    def _create_demo_order(self, user: Any, items: list, status: str) -> None:
        order = Order.objects.create(
            user=user,
            status=status,
            payment_method=Order.PaymentMethod.CARD,
            full_name=user.get_username(),
            email=user.email,
            phone=user.phone,
            shipping_address=user.default_address or "Demo address",
        )
        for product, quantity in items:
            OrderItem.objects.create(
                order=order, product=product, quantity=quantity, price=product.price
            )
        order.recalculate_total()
