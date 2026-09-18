from django.urls import path

from apps.payments.views import (
    PaymentCreateView,
    PaymentDetailView,
    PaymentListView,
)


urlpatterns = [
    path("", PaymentListView.as_view()),
    path(
        "orders/<int:order_id>/",
        PaymentCreateView.as_view(),
    ),
    path(
        "<int:pk>/",
        PaymentDetailView.as_view(),
    ),
]