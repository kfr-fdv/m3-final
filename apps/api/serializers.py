from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent")


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    in_stock = serializers.BooleanField(read_only=True)
    rating_avg = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)
    sold_qty = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "price",
            "category",
            "image",
            "stock",
            "in_stock",
            "rating_avg",
            "rating_count",
            "sold_qty",
            "created_at",
        )


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "user", "rating", "comment", "created_at")
        read_only_fields = ("id", "user", "created_at")


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.CharField(source="product.name", read_only=True)
    product_id = serializers.IntegerField(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("product_id", "product", "quantity", "price", "line_total")


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "status",
            "payment_method",
            "total_price",
            "full_name",
            "email",
            "phone",
            "shipping_address",
            "items",
            "can_cancel",
            "created_at",
        )
        read_only_fields = ("id", "status", "total_price", "items", "can_cancel", "created_at")


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "full_name",
            "email",
            "phone",
            "shipping_address",
            "payment_method",
            "items",
        )
        read_only_fields = ("id",)

    def validate_items(self, value: list) -> list:
        if not value:
            raise serializers.ValidationError("Замовлення повинно містити хоча б одну позицію.")
        return value

    def create(self, validated_data: dict) -> Order:
        from apps.orders.services import OutOfStock, create_order

        items = [(row["product"].pk, row["quantity"]) for row in validated_data.pop("items")]
        try:
            return create_order(
                self.context["request"].user,
                items,
                **validated_data,
            )
        except OutOfStock as exc:
            raise serializers.ValidationError(
                {"items": f"Недостатньо «{exc.product.name}» на складі."}
            ) from exc


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("status",)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data: dict) -> object:
        return User.objects.create_user(**validated_data)


class CartLineSerializer(serializers.Serializer):
    product = ProductSerializer(read_only=True)
    quantity = serializers.IntegerField(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)


class CartItemInputSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1, default=1)
