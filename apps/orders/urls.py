from django.urls import path

from apps.orders.views import (
    OrderCancelView,
    OrderListCreateView,
    OrderDetailView,
)


urlpatterns = [
    path("", OrderListCreateView.as_view()),
    path("<int:pk>/", OrderDetailView.as_view()),
    path("<int:pk>/cancel/", OrderCancelView.as_view()),
]