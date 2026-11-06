from rest_framework import serializers

from category.serializers import PriceTypeSerializer
from .models import PriceHistory


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ["id", "price_type", "price", "created_at", "updated_at", "notes"]
        read_only_fields = ["id", "price_type", "created_at", "updated_at"]


class PriceUpdateSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BulkPriceUpdateSerializer(serializers.Serializer):
    prices = serializers.DictField(
        child=serializers.DecimalField(max_digits=20, decimal_places=2, min_value=0),
        help_text="Mapping of price_type_id (str) to price value",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class PriceTypeWithLatestPriceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    category_id = serializers.IntegerField()
    category_name = serializers.CharField()
    source_currency = serializers.CharField()
    target_currency = serializers.CharField()
    trade_type = serializers.CharField()
    latest_price = serializers.DecimalField(max_digits=20, decimal_places=2, allow_null=True)
    latest_price_at = serializers.DateTimeField(allow_null=True)
