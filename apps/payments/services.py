from django.db import transaction
from django_fsm import TransitionNotAllowed
from apps.orders.services import confirm_order_stock, release_order_stock
from apps.orders.models import Order
from apps.payments.models import Payment


@transaction.atomic
def start_payment(payment: Payment) -> Payment:
    payment.start_processing()
    payment.save(update_fields=["status", "updated_at"])

    return payment


@transaction.atomic
def complete_payment(payment: Payment, transaction_id: str) -> Payment:
    payment.succeed()
    payment.transaction_id = transaction_id
    payment.save(
        update_fields=[
            "status",
            "transaction_id",
            "updated_at",
        ]
    )

    order = payment.order

    confirm_order_stock(order)

    order.mark_as_paid()
    order.save(update_fields=["status", "updated_at"])

    return payment


@transaction.atomic
def fail_payment(payment: Payment) -> Payment:
    payment.fail()
    payment.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return payment

@transaction.atomic
def create_payment(order: Order) -> Payment:
    order = (
        Order.objects
        .select_for_update()
        .get(pk=order.pk)
    )

    if order.status != Order.Status.PENDING_PAYMENT:
        raise ValueError(
            f"Order '{order.id}' is not pending payment."
        )

    active_payment_exists = order.payments.filter(
        status__in=[
            Payment.Status.PENDING,
            Payment.Status.PROCESSING,
        ]
    ).exists()

    if active_payment_exists:
        raise ValueError(
            "This order already has an active payment."
        )

    return Payment.objects.create(
        order=order,
        amount=order.total,
    )