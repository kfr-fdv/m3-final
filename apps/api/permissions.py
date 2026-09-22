from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwner(permissions.BasePermission):
    """Доступ до об'єкта лише його власнику (obj.user)."""

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        return getattr(obj, "user_id", None) == request.user.pk
