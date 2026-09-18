from django.db import models
from django_fsm import FSMField, transition

from apps.orders.models import Order


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
    )

    status = FSMField(
        default=Status.PENDING,
        choices=Status.choices,
        protected=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.pk} - Order #{self.order_id}"

    @transition(
        field=status,
        source=Status.PENDING,
        target=Status.PROCESSING,
    )
    def start_processing(self):
        pass

    @transition(
        field=status,
        source=Status.PROCESSING,
        target=Status.SUCCEEDED,
    )
    def succeed(self):
        pass

    @transition(
        field=status,
        source=Status.PROCESSING,
        target=Status.FAILED,
    )
    def fail(self):
        pass

    @transition(
        field=status,
        source=Status.SUCCEEDED,
        target=Status.REFUNDED,
    )
    def refund(self):
        pass