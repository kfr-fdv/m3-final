from typing import Any

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, permissions, views, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.catalog.filters import ProductFilter
from apps.catalog.models import Product
from apps.orders.cart import Cart
from apps.orders.models import Order
from apps.reviews.models import Review
from apps.reviews.services import can_review

from .permissions import IsOwner
from .serializers import (
    CartItemInputSerializer,
    CartLineSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
    ReviewSerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary="Список товарів",
        description=(
            "Пагінований список активних товарів. Підтримує фільтри "
            "(`category`, `in_stock`, `min_price`, `max_price`), пошук за назвою й "
            "описом (`search`) та сортування (`ordering`: price, created_at, "
            "rating_avg, sold_qty)."
        ),
    ),
    retrieve=extend_schema(
        summary="Деталі товару",
        responses={200: ProductSerializer, 404: OpenApiResponse(description="Товар не знайдено.")},
    ),
)
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Список та деталі товарів: пагінація, фільтри, пошук, сортування."""

    queryset = Product.objects.for_listing()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "rating_avg", "sold_qty"]


@extend_schema_view(
    get=extend_schema(summary="Відгуки товару"),
    post=extend_schema(
        summary="Залишити відгук",
        description="Створити відгук. Дозволено лише після покупки товару і лише один раз.",
        responses={
            201: ReviewSerializer,
            403: OpenApiResponse(
                description="Відгук недоступний: товар не куплено або відгук уже залишено."
            ),
        },
        examples=[
            OpenApiExample(
                "Відгук",
                value={"rating": 5, "comment": "Чудовий хміль, аромат — вогонь!"},
                request_only=True,
            ),
        ],
    ),
)
class ProductReviewsView(generics.ListCreateAPIView):
    """Відгуки товару: GET — список, POST — створити (лише після покупки)."""

    serializer_class = ReviewSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        return Review.objects.filter(product_id=self.kwargs["product_id"]).select_related("user")

    def perform_create(self, serializer: Any) -> None:
        product = get_object_or_404(Product, pk=self.kwargs["product_id"], is_active=True)
        if not can_review(self.request.user, product):
            raise PermissionDenied("Відгук можна залишити лише після покупки і лише раз.")
        serializer.save(product=product, user=self.request.user)


@extend_schema_view(
    get=extend_schema(summary="Мій відгук"),
    put=extend_schema(summary="Оновити свій відгук"),
    patch=extend_schema(summary="Оновити свій відгук (частково)"),
)
class ReviewUpdateView(generics.RetrieveUpdateAPIView):
    """Перегляд і редагування власного відгуку — доступно лише його автору."""

    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        # Тільки власні відгуки: чужий за id віддасть 404, а не 403.
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        return Review.objects.filter(user=self.request.user).select_related("user")


@extend_schema_view(
    list=extend_schema(summary="Мої замовлення"),
    retrieve=extend_schema(
        summary="Замовлення за ID",
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(
                description="Замовлення не знайдено або належить іншому користувачу."
            ),
        },
    ),
    create=extend_schema(
        summary="Створити замовлення",
        responses={
            201: OrderCreateSerializer,
            400: OpenApiResponse(
                description="Порожній кошик, неіснуючий товар або недостатньо на складі."
            ),
        },
        examples=[
            OpenApiExample(
                "Нове замовлення",
                value={
                    "full_name": "Олена Шевченко",
                    "email": "olena@example.com",
                    "phone": "+380991112233",
                    "shipping_address": "Київ, Відділення №1",
                    "payment_method": "card",
                    "items": [{"product": 1, "quantity": 2}],
                },
                request_only=True,
            ),
        ],
    ),
)
class OrderViewSet(viewsets.ModelViewSet):
    """Замовлення поточного користувача: перегляд і створення власних замовлень.

    Зміна статусу та скасування через API недоступні — це робить лише персонал.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwner]
    # Лише читання своїх замовлень і створення нового; статус/видалення закриті.
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderSerializer


@extend_schema(
    summary="Реєстрація користувача",
    examples=[
        OpenApiExample(
            "Новий користувач",
            value={
                "username": "newuser",
                "email": "user@example.com",
                "password": "StrongPass123!",
            },
            request_only=True,
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    """Реєстрація нового користувача."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class CartAPIView(views.APIView):
    """Кошик у сесії: GET перегляд, POST додати, PATCH оновити, DELETE видалити/очистити."""

    permission_classes = [permissions.AllowAny]
    serializer_class = CartLineSerializer

    def _data(self, cart: Cart) -> dict:
        return {
            "items": CartLineSerializer(list(cart), many=True).data,
            "total": cart.total,
        }

    @extend_schema(summary="Переглянути кошик", responses=CartLineSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(self._data(Cart(request.session)))

    @extend_schema(
        summary="Додати товар у кошик",
        request=CartItemInputSerializer,
        responses=CartLineSerializer(many=True),
    )
    def post(self, request: Request) -> Response:
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart(request.session)
        cart.add(serializer.validated_data["product"], serializer.validated_data["quantity"])
        return Response(self._data(cart))

    @extend_schema(
        summary="Встановити кількість товару",
        request=CartItemInputSerializer,
        responses=CartLineSerializer(many=True),
    )
    def patch(self, request: Request) -> Response:
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart(request.session)
        cart.update(
            serializer.validated_data["product"],
            serializer.validated_data["quantity"],
        )
        return Response(self._data(cart))

    @extend_schema(
        summary="Видалити товар або очистити кошик",
        description="Якщо передано `product` — видаляє цю позицію; без тіла — очищує весь кошик.",
        request=CartItemInputSerializer,
        responses=CartLineSerializer(many=True),
    )
    def delete(self, request: Request) -> Response:
        cart = Cart(request.session)
        data = request.data if isinstance(request.data, dict) else {}
        product_id = data.get("product")
        if product_id:
            cart.remove(get_object_or_404(Product, pk=product_id))
        else:
            cart.clear()
        return Response(self._data(cart))


@extend_schema(
    summary="Вхід (отримати JWT)",
    description="Приймає ім'я користувача та пароль, повертає пару токенів `access`/`refresh`.",
)
class LoginView(TokenObtainPairView):
    """Отримання JWT-токенів за логіном і паролем."""


@extend_schema(
    summary="Оновити access-токен",
    description="Приймає дійсний `refresh`-токен і повертає новий `access`-токен.",
)
class RefreshTokenView(TokenRefreshView):
    """Оновлення access-токена за refresh-токеном."""
