from django.db import models
from django_fsm import FSMField, transition

from apps.products.models import Product


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pending payment"
        PAID = "paid", "Paid"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    status = FSMField(
        default=Status.PENDING_PAYMENT,
        choices=Status.choices,
        protected=True,
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk}"

    @transition(
        field=status,
        source=Status.PENDING_PAYMENT,
        target=Status.PAID,
    )
    def mark_as_paid(self):
        pass

    @transition(
        field=status,
        source=Status.PAID,
        target=Status.PROCESSING,
    )
    def start_processing(self):
        pass

    @transition(
        field=status,
        source=Status.PROCESSING,
        target=Status.COMPLETED,
    )
    def complete(self):
        pass

    @transition(
        field=status,
        source=Status.PENDING_PAYMENT,
        target=Status.CANCELLED,
    )
    def cancel(self):
        pass


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    quantity = models.PositiveIntegerField()

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def subtotal(self):
        return self.quantity * self.unit_price