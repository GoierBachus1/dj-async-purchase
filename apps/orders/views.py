from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from apps.orders.serializers import OrderSerializer
from apps.orders.services import create_order
from apps.orders.models import Order
from django_fsm import TransitionNotAllowed
from apps.orders.tasks import expire_order
from apps.orders.models import Order
from apps.orders.serializers import OrderSerializer, OrderCreateSerializer
from apps.orders.services import cancel_order
from apps.products.models import Product

class OrderListCreateView(APIView):

    def get(self, request):
        orders = (
            Order.objects
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        serializer = OrderSerializer(
            orders,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        input_serializer = OrderCreateSerializer(
            data=request.data
        )
        input_serializer.is_valid(
            raise_exception=True
        )

        try:
            order = create_order(
                input_serializer.validated_data["items"]
            )

        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        expiration_task = expire_order.apply_async(
            args=[order.id],
            countdown=60,
        )

        serializer = OrderSerializer(order)

        return Response(
            {
                "order": serializer.data,
                "expiration_task_id": expiration_task.id,
            },
            status=status.HTTP_201_CREATED,
        )

class OrderDetailView(APIView):

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        serializer = OrderSerializer(order)

        return Response(serializer.data)


class OrderCancelView(APIView):

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        try:
            cancel_order(order)

        except TransitionNotAllowed:
            return Response(
                {
                    "detail": (
                        f"Order cannot be cancelled from "
                        f"status '{order.status}'."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OrderSerializer(order)

        return Response(serializer.data)


class OrderListView(APIView):

    def get(self, request):
        orders = (
            Order.objects
            .prefetch_related("items__product")
            .order_by("-created_at")
        )

        serializer = OrderSerializer(
            orders,
            many=True,
        )

        return Response(serializer.data)