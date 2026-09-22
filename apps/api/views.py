from typing import Any, cast

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, serializers, status, views, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response

from apps.catalog.filters import ProductFilter
from apps.catalog.models import Product
from apps.orders.cart import Cart
from apps.orders.models import Order
from apps.orders.services import cancel_order
from apps.reviews.models import Review
from apps.reviews.services import user_can_review

from .permissions import IsOwner
from .serializers import (
    CartItemInputSerializer,
    CartLineSerializer,
    OrderCreateSerializer,
    OrderSerializer,
    OrderStatusSerializer,
    ProductSerializer,
    RegisterSerializer,
    ReviewSerializer,
)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Список та деталі товарів: пагінація, фільтри, пошук, сортування."""

    queryset = Product.objects.for_listing()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["price", "created_at", "rating_avg", "sold_qty"]


class ProductReviewsView(generics.ListCreateAPIView):
    """Відгуки товару: GET — список, POST — створити (лише після покупки)."""

    serializer_class = ReviewSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Review.objects.none()
        return Review.objects.filter(product_id=self.kwargs["product_id"]).select_related("user")

    def perform_create(self, serializer: Any) -> None:
        product = get_object_or_404(Product, pk=self.kwargs["product_id"], is_active=True)
        if not user_can_review(self.request.user, product):
            raise PermissionDenied("Відгук можна залишити лише після покупки і лише раз.")
        serializer.save(product=product, user=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    """Замовлення поточного користувача: створення, перегляд, зміна статусу, скасування."""

    permission_classes = [permissions.IsAuthenticated, IsOwner]
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related("items__product")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action in ("update", "partial_update"):
            return OrderStatusSerializer
        return OrderSerializer

    def perform_update(self, serializer: Any) -> None:
        order = cast(Order, serializer.instance)
        new_status = serializer.validated_data.get("status", order.status)
        if (
            new_status == Order.OrderStatus.CANCELLED
            and order.status != Order.OrderStatus.CANCELLED
        ):
            if not cancel_order(order):
                raise serializers.ValidationError({"status": "Замовлення не можна скасувати."})
        else:
            serializer.save()

    def destroy(self, request: Request, *args: object, **kwargs: object) -> Response:
        order = self.get_object()
        if not cancel_order(order):
            return Response(
                {"detail": "Замовлення не можна скасувати."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


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

    @extend_schema(responses=CartLineSerializer(many=True))
    def get(self, request: Request) -> Response:
        return Response(self._data(Cart(request)))

    @extend_schema(request=CartItemInputSerializer, responses=CartLineSerializer(many=True))
    def post(self, request: Request) -> Response:
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart(request)
        cart.add(serializer.validated_data["product"], serializer.validated_data["quantity"])
        return Response(self._data(cart))

    @extend_schema(request=CartItemInputSerializer, responses=CartLineSerializer(many=True))
    def patch(self, request: Request) -> Response:
        serializer = CartItemInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cart = Cart(request)
        cart.add(
            serializer.validated_data["product"],
            serializer.validated_data["quantity"],
            replace=True,
        )
        return Response(self._data(cart))

    def delete(self, request: Request) -> Response:
        cart = Cart(request)
        data = request.data if isinstance(request.data, dict) else {}
        product_id = data.get("product")
        if product_id:
            cart.remove(get_object_or_404(Product, pk=product_id))
        else:
            cart.clear()
        return Response(self._data(cart))
