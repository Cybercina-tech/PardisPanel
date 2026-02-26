from rest_framework import serializers


class PriceItemSerializer(serializers.Serializer):
    """
    Serializer representing a single pricing item inside a category.

    This is intentionally not a ModelSerializer so we can flexibly
    shape the output structure around annotated / aggregated data.
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    pair = serializers.CharField()
    trade_type = serializers.CharField()
    latest_price = serializers.DecimalField(max_digits=20, decimal_places=2)
    latest_price_timestamp = serializers.DateTimeField()


class SpecialPriceItemSerializer(serializers.Serializer):
    """
    Serializer representing a special price entry.

    Items from `special_price.SpecialPriceType` appear under a synthetic
    "Special Prices" category in the API response.
    Only items with a recent special_price (last 6 hours) are included.
    When is_double_price is True, cash_price and account_price are present.
    """

    id = serializers.IntegerField()
    name = serializers.CharField()
    pair = serializers.CharField()
    trade_type = serializers.CharField()
    latest_special_price = serializers.DecimalField(max_digits=20, decimal_places=2)
    latest_special_price_timestamp = serializers.DateTimeField()
    is_double_price = serializers.BooleanField(default=False)
    cash_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, allow_null=True, required=False
    )
    account_price = serializers.DecimalField(
        max_digits=20, decimal_places=2, allow_null=True, required=False
    )


class CategoryPricingSerializer(serializers.Serializer):
    """
    Serializer for a single category and its items.

    - `id` may be `null` for synthetic categories (e.g. "Special Prices").
    - `items` will always be present (may be an empty list).
    """

    id = serializers.IntegerField(allow_null=True)
    name = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    description = serializers.CharField(allow_null=True)

    # For regular categories, this contains `PriceItemSerializer` data.
    # For the synthetic "Special Prices" category, this contains
    # `SpecialPriceItemSerializer` data. We keep this generic here and
    # rely on the view to supply appropriately-shaped dictionaries.
    items = serializers.ListField(child=serializers.DictField())


class PricingResponseSerializer(serializers.Serializer):
    """
    Top-level serializer for the pricing API response.

    This provides a stable, well-structured JSON schema for consumers
    such as dashboards, bots, or external services.
    """

    generated_at = serializers.DateTimeField()
    categories = CategoryPricingSerializer(many=True)


