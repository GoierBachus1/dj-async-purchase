from rest_framework import serializers

from apps.products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    available_stock = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "description",
            "price",
            "stock",
            "reserved_stock",
            "available_stock",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "reserved_stock",
            "available_stock",
            "created_at",
            "updated_at",
        ]