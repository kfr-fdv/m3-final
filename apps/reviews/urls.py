from django.urls import path

from .views import ReviewCreateView, ReviewUpdateView

app_name = "reviews"

urlpatterns = [
    path("product/<slug:slug>/review/", ReviewCreateView.as_view(), name="create"),
    path("review/<int:pk>/edit/", ReviewUpdateView.as_view(), name="edit"),
]
