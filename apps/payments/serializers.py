from rest_framework import serializers

from apps.payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "status",
            "amount",
            "transaction_id",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "status",
            "transaction_id",
            "created_at",
            "updated_at",
        ]