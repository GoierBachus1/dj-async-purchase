from decimal import Decimal

from django.db import transaction
from django_fsm import can_proceed
from apps.orders.models import Order, OrderItem
from apps.products.models import Product


@transaction.atomic
def create_order(items: list[dict]) -> Order:
    order = Order.objects.create(total=Decimal("0.00"))

    total = Decimal("0.00")

    for item in items:
        product_id = item["product_id"]
        quantity = item["quantity"]

        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero.")

        product = Product.objects.select_for_update().get(
            pk=product_id,
            is_active=True,
        )

        if product.available_stock < quantity:
            raise ValueError(
                f"Insufficient stock for product '{product.name}'."
            )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=product.price,
        )

        product.reserved_stock += quantity
        product.save(
            update_fields=["reserved_stock", "updated_at"]
        )

        total += product.price * quantity

    order.total = total
    order.save(
        update_fields=["total", "updated_at"]
    )

    return order


@transaction.atomic
def confirm_order_stock(order: Order) -> Order:
    for item in order.items.select_related("product").all():
        product = Product.objects.select_for_update().get(
            pk=item.product_id
        )

        if product.reserved_stock < item.quantity:
            raise ValueError(
                f"Invalid reserved stock for product '{product.name}'."
            )

        if product.stock < item.quantity:
            raise ValueError(
                f"Insufficient physical stock for product '{product.name}'."
            )

        product.stock -= item.quantity
        product.reserved_stock -= item.quantity

        product.save(
            update_fields=[
                "stock",
                "reserved_stock",
                "updated_at",
            ]
        )

    return order


@transaction.atomic
def release_order_stock(order: Order) -> Order:
    for item in order.items.select_related("product").all():
        product = Product.objects.select_for_update().get(
            pk=item.product_id
        )

        if product.reserved_stock < item.quantity:
            raise ValueError(
                f"Invalid reserved stock for product '{product.name}'."
            )

        product.reserved_stock -= item.quantity

        product.save(
            update_fields=[
                "reserved_stock",
                "updated_at",
            ]
        )

    return order

@transaction.atomic
def cancel_order(order: Order) -> Order:
    order.cancel()

    release_order_stock(order)

    order.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    return order