from rest_framework import serializers

from .models import Finalization, FinalizedPriceHistory, SpecialPriceFinalization


class FinalizedPriceHistorySerializer(serializers.ModelSerializer):
    price_type_name = serializers.CharField(source="price_history.price_type.name", read_only=True)
    price = serializers.DecimalField(
        source="price_history.price", max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = FinalizedPriceHistory
        fields = ["id", "price_history", "price_type_name", "price"]


class FinalizationSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    channel_name = serializers.CharField(source="channel.name", read_only=True, default=None)
    finalized_by_name = serializers.CharField(
        source="finalized_by.get_full_name", read_only=True, default=None
    )
    finalized_prices = FinalizedPriceHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Finalization
        fields = [
            "id", "category", "category_name", "channel", "channel_name",
            "finalized_at", "finalized_by", "finalized_by_name",
            "message_sent", "image_caption", "telegram_response", "notes",
            "finalized_prices",
        ]


class SpecialPriceFinalizationSerializer(serializers.ModelSerializer):
    special_price_type_name = serializers.CharField(
        source="special_price_history.special_price_type.name", read_only=True
    )
    price = serializers.DecimalField(
        source="special_price_history.price", max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = SpecialPriceFinalization
        fields = [
            "id", "special_price_history", "special_price_type_name", "price",
            "channel", "finalized_at", "finalized_by",
            "message_sent", "image_caption", "telegram_response", "notes",
        ]


class FinalizeCategoryRequestSerializer(serializers.Serializer):
    channel_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FinalizeSpecialPriceRequestSerializer(serializers.Serializer):
    channel_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FinalizeAllRequestSerializer(serializers.Serializer):
    channel_id = serializers.IntegerField()
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )
    special_price_history_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )


class PendingPriceSerializer(serializers.Serializer):
    price_type_id = serializers.IntegerField()
    price_type_name = serializers.CharField()
    price_history_id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=20, decimal_places=2)
    created_at = serializers.DateTimeField()


class PendingCategorySerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    category_name = serializers.CharField()
    pending_prices = PendingPriceSerializer(many=True)


class PendingSpecialPriceSerializer(serializers.Serializer):
    special_price_type_id = serializers.IntegerField()
    special_price_type_name = serializers.CharField()
    price_history_id = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=20, decimal_places=2)
    created_at = serializers.DateTimeField()
