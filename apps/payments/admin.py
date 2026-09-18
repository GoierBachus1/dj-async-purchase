from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "status",
        "amount",
        "transaction_id",
        "created_at",
    )

    list_filter = ("status",)

    readonly_fields = (
        "status",
        "created_at",
        "updated_at",
    )