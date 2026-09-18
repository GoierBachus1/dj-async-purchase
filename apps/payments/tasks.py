from celery import shared_task
from django.db import transaction

from apps.payments.models import Payment
from apps.payments.services import (
    complete_payment,
    fail_payment,
    start_payment,
)


@shared_task
def test_celery():
    return "Celery is working"


@shared_task
def process_payment_async(payment_id: int):
    with transaction.atomic():
        payment = (
            Payment.objects
            .select_for_update()
            .select_related("order")
            .get(pk=payment_id)
        )

        if payment.status == Payment.Status.SUCCEEDED:
            return {
                "payment_id": payment.id,
                "status": "already_succeeded",
            }

        if payment.status == Payment.Status.FAILED:
            return {
                "payment_id": payment.id,
                "status": "already_failed",
            }

        if payment.status == Payment.Status.PENDING:
            start_payment(payment)

        # Simulación temporal del proveedor
        payment_successful = True

        if payment_successful:
            complete_payment(
                payment,
                transaction_id=f"TXN-{payment.id}",
            )

            return {
                "payment_id": payment.id,
                "status": "succeeded",
            }

        fail_payment(payment)

        return {
            "payment_id": payment.id,
            "status": "failed",
        }