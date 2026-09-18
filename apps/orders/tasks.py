from celery import shared_task
from django_fsm import TransitionNotAllowed

from apps.orders.models import Order
from apps.orders.services import cancel_order


@shared_task
def expire_order(order_id: int):
    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return {
            "order_id": order_id,
            "status": "not_found",
        }

    if order.status != Order.Status.PENDING_PAYMENT:
        return {
            "order_id": order.id,
            "status": "ignored",
            "order_status": order.status,
        }

    try:
        cancel_order(order)
    except TransitionNotAllowed:
        return {
            "order_id": order.id,
            "status": "ignored",
            "order_status": order.status,
        }

    return {
        "order_id": order.id,
        "status": "expired",
    }