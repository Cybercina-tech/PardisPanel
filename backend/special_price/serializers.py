from rest_framework import serializers

from category.serializers import CurrencySerializer
from .models import SpecialPriceHistory, SpecialPricePair, SpecialPriceType


class SpecialPriceHistorySerializer(serializers.ModelSerializer):
    pair_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = SpecialPriceHistory
        fields = [
            "id",
            "special_price_type",
            "pair_id",
            "price",
            "cash_price",
            "account_price",
            "created_at",
            "updated_at",
            "notes",
        ]
        read_only_fields = ["id", "special_price_type", "pair_id", "created_at", "updated_at"]


class SpecialPricePairSerializer(serializers.ModelSerializer):
    source_currency = CurrencySerializer(read_only=True)
    target_currency = CurrencySerializer(read_only=True)
    latest_price = serializers.SerializerMethodField()

    class Meta:
        model = SpecialPricePair
        fields = [
            "id",
            "name",
            "source_currency",
            "target_currency",
            "trade_type",
            "latest_price",
            "created_at",
            "updated_at",
        ]

    def get_latest_price(self, obj):
        latest = obj.histories.order_by("-created_at").first()
        if latest:
            return {
                "id": latest.id,
                "price": str(latest.price),
                "created_at": latest.created_at,
            }
        return None


class SpecialPricePairInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    source_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialPriceType.source_currency.field.related_model.objects.all(),
        source="source_currency",
    )
    target_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialPriceType.target_currency.field.related_model.objects.all(),
        source="target_currency",
    )
    trade_type = serializers.ChoiceField(choices=SpecialPriceType.TRADE_CHOICES)

    def validate(self, attrs):
        attrs["name"] = attrs["name"].strip()
        if not attrs["name"]:
            raise serializers.ValidationError({"name": "Pair name is required."})
        if attrs["source_currency"].id == attrs["target_currency"].id:
            raise serializers.ValidationError(
                {"target_currency_id": "Source and target currency cannot be the same."}
            )
        return attrs


class SpecialPriceTypeSerializer(serializers.ModelSerializer):
    source_currency = CurrencySerializer(read_only=True)
    target_currency = CurrencySerializer(read_only=True)
    source_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialPriceType.source_currency.field.related_model.objects.all(),
        source="source_currency",
        write_only=True,
    )
    target_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=SpecialPriceType.target_currency.field.related_model.objects.all(),
        source="target_currency",
        write_only=True,
    )
    latest_price = serializers.SerializerMethodField()
    pairs = SpecialPricePairSerializer(many=True, read_only=True)
    pair_inputs = SpecialPricePairInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = SpecialPriceType
        fields = [
            "id", "name", "slug", "icon",
            "source_currency", "target_currency",
            "source_currency_id", "target_currency_id",
            "trade_type", "description", "is_double_price",
            "created_at", "updated_at",
            "latest_price",
            "pairs",
            "pair_inputs",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]
        extra_kwargs = {
            "trade_type": {"required": False},
        }

    def get_latest_price(self, obj):
        latest = obj.special_price_histories.select_related("pair").order_by("-created_at").first()
        if latest:
            return {
                "id": latest.id,
                "pair_id": latest.pair_id,
                "price": str(latest.price),
                "created_at": latest.created_at,
            }
        return None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        pair_inputs = attrs.get("pair_inputs")
        if self.instance is None and not pair_inputs and (
            "source_currency" not in attrs or "target_currency" not in attrs
        ):
            raise serializers.ValidationError(
                {"pair_inputs": "At least one currency pair is required."}
            )

        if pair_inputs:
            seen = set()
            trade_types = set()
            for index, pair_data in enumerate(pair_inputs):
                key = (
                    pair_data["name"].lower(),
                    pair_data["source_currency"].id,
                    pair_data["target_currency"].id,
                    pair_data["trade_type"],
                )
                if key in seen:
                    raise serializers.ValidationError(
                        {"pair_inputs": f"Duplicate pair at row {index + 1}."}
                    )
                seen.add(key)
                trade_types.add(pair_data["trade_type"])
            if len(pair_inputs) > 1 and len(trade_types) == 1:
                raise serializers.ValidationError(
                    {
                        "pair_inputs": (
                            "When submitting multiple pairs, include both buy and sell rows."
                        )
                    }
                )
        elif pair_inputs == []:
            raise serializers.ValidationError(
                {"pair_inputs": "At least one currency pair is required."}
            )
        return attrs

    def create(self, validated_data):
        pair_inputs = validated_data.pop("pair_inputs", None)
        if pair_inputs and "trade_type" not in validated_data:
            validated_data["trade_type"] = pair_inputs[0]["trade_type"]
        special_price = super().create(validated_data)

        if pair_inputs:
            pair_models = [
                SpecialPricePair(
                    special_price_type=special_price,
                    source_currency=pair["source_currency"],
                    target_currency=pair["target_currency"],
                    trade_type=pair["trade_type"],
                    name=pair["name"],
                )
                for pair in pair_inputs
            ]
            SpecialPricePair.objects.bulk_create(pair_models)
            first_pair = pair_models[0]
            special_price.source_currency = first_pair.source_currency
            special_price.target_currency = first_pair.target_currency
            special_price.trade_type = first_pair.trade_type
            special_price.save(
                update_fields=["source_currency", "target_currency", "trade_type", "updated_at"]
            )
        else:
            SpecialPricePair.objects.create(
                special_price_type=special_price,
                source_currency=special_price.source_currency,
                target_currency=special_price.target_currency,
                trade_type=special_price.trade_type,
                name=special_price.name,
            )
        return special_price

    def update(self, instance, validated_data):
        pair_inputs = validated_data.pop("pair_inputs", None)
        special_price = super().update(instance, validated_data)

        if pair_inputs is not None:
            existing_pairs = {
                (pair.name.lower(), pair.source_currency_id, pair.target_currency_id, pair.trade_type): pair
                for pair in special_price.pairs.all()
            }
            desired_keys = {
                (
                    pair["name"].lower(),
                    pair["source_currency"].id,
                    pair["target_currency"].id,
                    pair["trade_type"],
                ): pair
                for pair in pair_inputs
            }

            for key, pair in existing_pairs.items():
                if key not in desired_keys:
                    pair.delete()

            for key, pair in desired_keys.items():
                if key not in existing_pairs:
                    SpecialPricePair.objects.create(
                        special_price_type=special_price,
                        source_currency=pair["source_currency"],
                        target_currency=pair["target_currency"],
                        trade_type=pair["trade_type"],
                        name=pair["name"],
                    )

            first = special_price.pairs.order_by("id").first()
            if first:
                special_price.source_currency = first.source_currency
                special_price.target_currency = first.target_currency
                special_price.trade_type = first.trade_type
                special_price.save(
                    update_fields=["source_currency", "target_currency", "trade_type", "updated_at"]
                )
        return special_price


class SpecialPriceUpdateSerializer(serializers.Serializer):
    pair_id = serializers.IntegerField(required=True)
    # Single-price types send ``price``; double-price types (Cash + Account on one
    # banner) send ``cash_price`` and ``account_price``. The view enforces which.
    price = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=0, required=False)
    cash_price = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=0, required=False)
    account_price = serializers.DecimalField(max_digits=20, decimal_places=2, min_value=0, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
