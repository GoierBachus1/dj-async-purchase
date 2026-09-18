from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.serializers import PaymentSerializer
from apps.payments.tasks import process_payment_async
from apps.payments.services import create_payment

class PaymentCreateView(APIView):

    def post(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)

        if order.status != Order.Status.PENDING_PAYMENT:
            return Response(
                {
                    "detail": "This order is not pending payment."
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            payment = create_payment(order)

        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_409_CONFLICT,
            )

        task = process_payment_async.delay(payment.id)

        serializer = PaymentSerializer(payment)

        return Response(
            {
                "payment": serializer.data,
                "task_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED,
        )

class PaymentDetailView(APIView):

    def get(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)

        serializer = PaymentSerializer(payment)

        return Response(serializer.data)


class PaymentListView(APIView):

    def get(self, request):
        payments = (
            Payment.objects
            .select_related("order")
            .order_by("-created_at")
        )

        serializer = PaymentSerializer(
            payments,
            many=True,
        )

        return Response(serializer.data)