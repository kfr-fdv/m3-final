"""Fill the database with a realistic Hop & Barley demo shop.

Safe to run many times: categories, products and users are matched by slug/username,
and orders with reviews are created only for demo customers that have none yet.
"""

import random
import shutil
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

DEMO_PASSWORD = "demo-pass-123"

# Root category -> subcategories. Products point to a subcategory slug.
CATEGORIES: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("Hops", "hops"): [
        ("Aroma Hops", "aroma-hops"),
        ("Bittering Hops", "bittering-hops"),
        ("Dual-Purpose Hops", "dual-purpose-hops"),
    ],
    ("Malts", "malts"): [
        ("Base Malts", "base-malts"),
        ("Specialty Malts", "specialty-malts"),
        ("Adjuncts", "adjuncts"),
    ],
    ("Yeast", "yeast"): [
        ("Ale Yeast", "ale-yeast"),
        ("Lager Yeast", "lager-yeast"),
        ("Wheat & Belgian Yeast", "wheat-belgian-yeast"),
    ],
    ("Brewing Kits", "brewing-kits"): [
        ("Beginner Kits", "beginner-kits"),
        ("All-Grain Kits", "all-grain-kits"),
        ("Extract Kits", "extract-kits"),
    ],
    ("Equipment", "equipment"): [
        ("Fermenters", "fermenters"),
        ("Kettles & Burners", "kettles-burners"),
        ("Bottling", "bottling"),
        ("Measuring", "measuring"),
    ],
    ("Additives", "additives"): [
        ("Finings & Clarifiers", "finings"),
        ("Water Treatment", "water-treatment"),
        ("Spices & Flavours", "spices-flavours"),
    ],
}

HOP_IMAGES = [
    "citra_hops.jpg",
    "cascade_hops.jpg",
    "mosaic_hops.jpg",
    "saaz_hops.jpg",
    "centennial_hops.jpg",
]
MALT_IMAGES = ["maris_otter_malt.jpg", "pilsner_malt.jpg", "caramel_malt.jpg", "unmalted_wheat.jpg"]
YEAST_IMAGES = ["safale_us05_yeast.jpg", "imperial_yeast.jpg"]
KIT_IMAGES = ["ipa_kit.jpg"]

# (name, subcategory slug, price, stock, image or None, description)
PRODUCTS: list[tuple[str, str, str, int, str | None, str]] = [
    # Hops
    (
        "Citra Hops 100g",
        "aroma-hops",
        "5.99",
        40,
        "citra_hops.jpg",
        "Bright citrus, mango and passion fruit. The backbone of modern IPAs.",
    ),
    (
        "Mosaic Hops 100g",
        "aroma-hops",
        "6.49",
        25,
        "mosaic_hops.jpg",
        "Blueberry, tropical fruit and pine. Great for hazy and New England IPAs.",
    ),
    (
        "Cascade Hops 100g",
        "aroma-hops",
        "4.49",
        35,
        "cascade_hops.jpg",
        "The classic American aroma hop: grapefruit, flowers and a light spice.",
    ),
    (
        "Saaz Hops 100g",
        "aroma-hops",
        "4.99",
        30,
        "saaz_hops.jpg",
        "Noble Czech hop with soft herbal and earthy notes for pilsners.",
    ),
    (
        "Nelson Sauvin Hops 100g",
        "aroma-hops",
        "7.99",
        0,
        "mosaic_hops.jpg",
        "White wine and gooseberry character from New Zealand. Currently sold out.",
    ),
    (
        "Magnum Hops 100g",
        "bittering-hops",
        "3.99",
        60,
        "centennial_hops.jpg",
        "Clean, high-alpha bittering hop that never gets harsh.",
    ),
    (
        "Warrior Hops 100g",
        "bittering-hops",
        "4.29",
        45,
        "cascade_hops.jpg",
        "Very smooth bitterness for double IPAs and imperial stouts.",
    ),
    (
        "Columbus Hops 100g",
        "bittering-hops",
        "4.59",
        20,
        "centennial_hops.jpg",
        "Pungent, resinous bittering with a dank finish.",
    ),
    (
        "Centennial Hops 100g",
        "dual-purpose-hops",
        "5.49",
        18,
        "centennial_hops.jpg",
        "Floral and citrus, often called 'super Cascade'.",
    ),
    (
        "Simcoe Hops 100g",
        "dual-purpose-hops",
        "6.99",
        22,
        "citra_hops.jpg",
        "Pine, passion fruit and earth. Works for both bittering and dry hopping.",
    ),
    (
        "Chinook Hops 100g",
        "dual-purpose-hops",
        "4.79",
        3,
        "saaz_hops.jpg",
        "Spicy grapefruit and pine for West Coast styles. Almost sold out.",
    ),
    # Malts
    (
        "Maris Otter Malt 5kg",
        "base-malts",
        "14.99",
        30,
        "maris_otter_malt.jpg",
        "Premium British pale base malt with a rich biscuit flavour.",
    ),
    (
        "Pilsner Malt 5kg",
        "base-malts",
        "12.49",
        40,
        "pilsner_malt.jpg",
        "Very light base malt for lagers, pilsners and Belgian ales.",
    ),
    (
        "Pale Ale Malt 5kg",
        "base-malts",
        "12.99",
        35,
        "maris_otter_malt.jpg",
        "Versatile base malt for pale ales and IPAs.",
    ),
    (
        "Munich Malt 1kg",
        "base-malts",
        "3.99",
        25,
        "pilsner_malt.jpg",
        "Adds malty depth and an amber colour to lagers and bocks.",
    ),
    (
        "Caramel Malt 60L 1kg",
        "specialty-malts",
        "3.79",
        45,
        "caramel_malt.jpg",
        "Adds sweetness, body and a toffee colour.",
    ),
    (
        "Chocolate Malt 500g",
        "specialty-malts",
        "2.99",
        30,
        "caramel_malt.jpg",
        "Roasted cocoa and coffee notes for porters and stouts.",
    ),
    (
        "Roasted Barley 500g",
        "specialty-malts",
        "2.79",
        28,
        "caramel_malt.jpg",
        "Dry, sharp roast that defines an Irish stout.",
    ),
    (
        "Carapils 1kg",
        "specialty-malts",
        "3.49",
        0,
        "pilsner_malt.jpg",
        "Improves foam and body without changing colour. Out of stock.",
    ),
    (
        "Unmalted Wheat 1kg",
        "adjuncts",
        "2.99",
        50,
        "unmalted_wheat.jpg",
        "For witbier and hazy styles. Improves head retention.",
    ),
    (
        "Flaked Oats 1kg",
        "adjuncts",
        "2.49",
        40,
        "unmalted_wheat.jpg",
        "Silky mouthfeel for hazy IPAs and oatmeal stouts.",
    ),
    (
        "Rice Hulls 500g",
        "adjuncts",
        "1.99",
        35,
        None,
        "Prevents a stuck mash when you brew with lots of wheat or oats.",
    ),
    # Yeast
    (
        "Safale US-05",
        "ale-yeast",
        "4.29",
        70,
        "safale_us05_yeast.jpg",
        "Clean American ale yeast, very forgiving for beginners.",
    ),
    (
        "Safale S-04",
        "ale-yeast",
        "4.29",
        55,
        "safale_us05_yeast.jpg",
        "English ale yeast that drops clear fast.",
    ),
    (
        "Imperial Juice A38",
        "ale-yeast",
        "8.99",
        15,
        "imperial_yeast.jpg",
        "Liquid yeast that boosts juicy hop character in hazy IPAs.",
    ),
    (
        "Saflager W-34/70",
        "lager-yeast",
        "5.49",
        40,
        "safale_us05_yeast.jpg",
        "The classic German lager strain, clean and crisp.",
    ),
    (
        "Imperial Global L13",
        "lager-yeast",
        "9.49",
        8,
        "imperial_yeast.jpg",
        "Liquid lager yeast for Helles and pilsners.",
    ),
    (
        "Safbrew WB-06",
        "wheat-belgian-yeast",
        "4.79",
        30,
        "safale_us05_yeast.jpg",
        "Banana and clove esters for German wheat beers.",
    ),
    (
        "Belgian Saison Yeast",
        "wheat-belgian-yeast",
        "5.99",
        12,
        "imperial_yeast.jpg",
        "Dry, peppery and fruity. Loves warm fermentation.",
    ),
    # Kits
    (
        "First Brew Pale Ale Kit",
        "beginner-kits",
        "39.99",
        20,
        "ipa_kit.jpg",
        "Everything for your first 5 litres of pale ale, with step-by-step guide.",
    ),
    (
        "Starter Equipment Set",
        "beginner-kits",
        "59.99",
        10,
        None,
        "Fermenter, airlock, sanitiser, siphon and hydrometer in one box.",
    ),
    (
        "West Coast IPA All-Grain Kit",
        "all-grain-kits",
        "60.00",
        10,
        "ipa_kit.jpg",
        "All-grain kit for 20 litres of bitter, piney West Coast IPA.",
    ),
    (
        "Hazy NEIPA All-Grain Kit",
        "all-grain-kits",
        "64.00",
        7,
        "ipa_kit.jpg",
        "Oats, wheat and a mountain of Citra and Mosaic for 20 litres.",
    ),
    (
        "Irish Stout All-Grain Kit",
        "all-grain-kits",
        "52.00",
        0,
        "ipa_kit.jpg",
        "Roasty, dry and creamy. Back in stock soon.",
    ),
    (
        "Czech Pilsner Extract Kit",
        "extract-kits",
        "34.99",
        15,
        "ipa_kit.jpg",
        "Malt extract kit with Saaz hops. No mashing needed.",
    ),
    (
        "Belgian Wit Extract Kit",
        "extract-kits",
        "36.99",
        12,
        "ipa_kit.jpg",
        "Coriander and orange peel included.",
    ),
    # Equipment (no photos on purpose: the logo placeholder is shown)
    (
        "Plastic Fermenter 30L",
        "fermenters",
        "24.99",
        25,
        None,
        "Food-grade bucket with lid, tap and airlock grommet.",
    ),
    (
        "Glass Carboy 23L",
        "fermenters",
        "44.99",
        6,
        None,
        "Crystal-clear glass so you can watch fermentation.",
    ),
    (
        "Stainless Kettle 35L",
        "kettles-burners",
        "119.00",
        5,
        None,
        "Heavy-bottom kettle with ball valve and thermometer port.",
    ),
    (
        "Gas Burner 7kW",
        "kettles-burners",
        "69.00",
        4,
        None,
        "Powerful outdoor burner for full-volume boils.",
    ),
    ("Bottle Capper", "bottling", "18.99", 30, None, "Bench capper for standard 26mm crown caps."),
    ("Crown Caps x100", "bottling", "4.99", 80, None, "Oxygen-absorbing crown caps in gold."),
    (
        "Brown Bottles 0.5L x12",
        "bottling",
        "11.99",
        40,
        None,
        "Returnable-style amber glass that protects beer from light.",
    ),
    (
        "Hydrometer with Jar",
        "measuring",
        "9.99",
        35,
        None,
        "Measure original and final gravity to calculate ABV.",
    ),
    (
        "Digital Thermometer",
        "measuring",
        "12.49",
        25,
        None,
        "Fast probe thermometer for mash and fermentation.",
    ),
    (
        "Refractometer",
        "measuring",
        "29.99",
        0,
        None,
        "Gravity from two drops of wort. Out of stock.",
    ),
    # Additives
    ("Irish Moss 50g", "finings", "2.49", 60, None, "Kettle finings for clearer beer."),
    (
        "Gelatin Finings",
        "finings",
        "3.29",
        45,
        None,
        "Cold-side clarifier for crystal-clear lagers.",
    ),
    (
        "Gypsum 100g",
        "water-treatment",
        "2.99",
        50,
        None,
        "Accentuates hop bitterness in pale ales and IPAs.",
    ),
    (
        "Calcium Chloride 100g",
        "water-treatment",
        "3.19",
        40,
        None,
        "Rounds out malt sweetness and body.",
    ),
    (
        "Coriander Seeds 50g",
        "spices-flavours",
        "1.99",
        30,
        None,
        "Essential spice for Belgian witbier.",
    ),
    (
        "Bitter Orange Peel 50g",
        "spices-flavours",
        "2.49",
        30,
        None,
        "Dried Curaçao orange peel for witbier and Belgian ales.",
    ),
    (
        "Vanilla Pods x2",
        "spices-flavours",
        "6.99",
        10,
        None,
        "Madagascar vanilla for stouts and porters.",
    ),
    (
        "Archive: Old Hop Sampler",
        "aroma-hops",
        "9.99",
        5,
        "saaz_hops.jpg",
        "Inactive product: must not appear in the catalog.",
    ),
]
INACTIVE = {"Archive: Old Hop Sampler"}

CUSTOMERS = [
    ("olena", "Olena", "Kovalenko", "Kyiv, Khreshchatyk St 12, apt 4"),
    ("taras", "Taras", "Shevchuk", "Lviv, Svobody Ave 28"),
    ("iryna", "Iryna", "Melnyk", "Odesa, Derybasivska St 5"),
    ("andrii", "Andrii", "Bondarenko", "Kharkiv, Sumska St 40"),
    ("maria", "Maria", "Tkachenko", "Dnipro, Yavornytskoho Ave 100"),
    ("dmytro", "Dmytro", "Kravchenko", "Vinnytsia, Soborna St 7"),
    ("sofia", "Sofia", "Oliinyk", "Ivano-Frankivsk, Nezalezhnosti St 3"),
    ("petro", "Petro", "Lysenko", "Chernihiv, Myru Ave 19"),
    ("kateryna", "Kateryna", "Moroz", "Poltava, Shevchenka St 22"),
    ("oleh", "Oleh", "Savchenko", "Uzhhorod, Korzo St 9"),
]

COMMENTS = {
    5: [
        "Absolutely brilliant, will buy again.",
        "Best batch I have ever brewed.",
        "Fresh, aromatic, fast delivery.",
        "Exactly as described. Love it.",
    ],
    4: [
        "Very good, just a bit pricey.",
        "Great quality, packaging could be better.",
        "Solid choice, no complaints.",
        "Works great, delivery took a few days.",
    ],
    3: ["Decent, but I expected more aroma.", "Okay for the price.", "Fine, nothing special."],
    2: ["Arrived later than promised.", "Aroma was weaker than expected."],
    1: ["Package was damaged.", "Not what I expected at all."],
}

# How much customers like each subcategory: shifts the ratings so sorting by rating is interesting.
QUALITY = {
    "aroma-hops": 4.6,
    "all-grain-kits": 4.5,
    "ale-yeast": 4.4,
    "base-malts": 4.2,
    "fermenters": 3.6,
}
STATUS_WEIGHTS = [
    ("delivered", 50),
    ("shipped", 15),
    ("paid", 15),
    ("pending", 12),
    ("cancelled", 8),
]
PURCHASED = {"paid", "shipped", "delivered"}


CUSTOMER_ADDRESSES = {username: address for username, _, _, address in CUSTOMERS}


class Command(BaseCommand):
    help = "Fill the database with a demo Hop & Barley catalog, customers, orders and reviews."

    def handle(self, *args: Any, **options: Any) -> None:
        random.seed(42)
        with transaction.atomic():
            self.copy_images()
            categories = self.seed_categories()
            products = self.seed_products(categories)
            customers = self.seed_customers()
            orders, reviews = self.seed_orders_and_reviews(customers, products)

        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {len(categories)}, products: {len(products)}, customers: {len(customers)}, "
                f"new orders: {orders}, new reviews: {reviews}"
            )
        )
        self.stdout.write(f"Demo customers log in with password: {DEMO_PASSWORD}")

    def copy_images(self) -> None:
        source = Path(settings.BASE_DIR) / "static" / "img" / "products"
        target = Path(settings.MEDIA_ROOT) / "products"
        target.mkdir(parents=True, exist_ok=True)
        for image in source.glob("*.jpg"):
            if not (target / image.name).exists():
                shutil.copy(image, target / image.name)

    def seed_categories(self) -> dict[str, Category]:
        categories: dict[str, Category] = {}
        for (root_name, root_slug), children in CATEGORIES.items():
            root, _ = Category.objects.get_or_create(slug=root_slug, defaults={"name": root_name})
            categories[root_slug] = root
            for name, slug in children:
                child, _ = Category.objects.get_or_create(
                    slug=slug, defaults={"name": name, "parent": root}
                )
                categories[slug] = child
        return categories

    def seed_products(self, categories: dict[str, Category]) -> list[Product]:
        products = []
        now = timezone.now()
        for index, (name, category_slug, price, stock, image, description) in enumerate(PRODUCTS):
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": categories[category_slug],
                    "price": Decimal(price),
                    "stock": stock,
                    "image": f"products/{image}" if image else "",
                    "description": description,
                    "is_active": name not in INACTIVE,
                },
            )
            if created:
                # The first products in the list are the "newest": photos come first in the catalog.
                created_at = now - timedelta(minutes=index)
                Product.objects.filter(pk=product.pk).update(created_at=created_at)
            products.append(product)
        return products

    def seed_customers(self) -> list[User]:
        customers = []
        for index, (username, first, last, address) in enumerate(CUSTOMERS, start=1):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "email": f"{username}@example.com",
                    "phone": f"+38050{index:07d}",
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            customers.append(user)
        return customers

    def seed_orders_and_reviews(
        self, customers: list[User], products: list[Product]
    ) -> tuple[int, int]:
        sellable = [p for p in products if p.is_active]
        statuses, weights = zip(*STATUS_WEIGHTS, strict=True)
        now = timezone.now()
        orders_created = reviews_created = 0

        for customer in customers:
            if customer.orders.exists():
                continue
            for _ in range(random.randint(2, 6)):
                status = random.choices(statuses, weights=weights)[0]
                order = Order.objects.create(
                    user=customer,
                    status=status,
                    last_name=customer.last_name,
                    first_name=customer.first_name,
                    email=customer.email,
                    phone=customer.phone,
                    payment_method=random.choice(Order.PaymentMethod.values),
                    shipping_address=CUSTOMER_ADDRESSES[customer.username],
                )
                for product in random.sample(sellable, k=random.randint(1, 4)):
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=random.randint(1, 5),
                        price=product.price,
                    )
                order.recalculate_total()
                created_at = now - timedelta(
                    days=random.randint(1, 120), hours=random.randint(0, 23)
                )
                Order.objects.filter(pk=order.pk).update(
                    created_at=created_at, updated_at=created_at
                )
                orders_created += 1

                if status not in PURCHASED:
                    continue
                for item in order.items.select_related("product__category"):
                    if random.random() > 0.6:
                        continue
                    if Review.objects.filter(user=customer, product=item.product).exists():
                        continue
                    rating = self.pick_rating(item.product.category.slug)
                    Review.objects.create(
                        product=item.product,
                        user=customer,
                        rating=rating,
                        comment=random.choice(COMMENTS[rating]),
                    )
                    reviews_created += 1
        return orders_created, reviews_created

    @staticmethod
    def pick_rating(category_slug: str) -> int:
        mean = QUALITY.get(category_slug, 4.0)
        return max(1, min(5, round(random.gauss(mean, 0.9))))
