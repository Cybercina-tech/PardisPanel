import math

from rest_framework import serializers

from .models import Category, Currency, PriceType


def _json_safe_api_float(value):
    """Avoid NaN/inf in JSON (breaks DRF JSONRenderer → 500)."""
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _resolve_preview_template(category_obj):
    template = getattr(category_obj, "last_used_template", None)
    if template and getattr(template, "image", None):
        return template
    # Fallback for newly saved templates before finalize/publish sets last_used_template.
    from template_editor.models import Template

    return (
        Template.objects.filter(category=category_obj, is_active=True)
        .exclude(image="")
        .order_by("-updated_at", "-id")
        .first()
    )


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol"]


class PriceTypeSerializer(serializers.ModelSerializer):
    source_currency = CurrencySerializer(read_only=True)
    target_currency = CurrencySerializer(read_only=True)
    source_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), source="source_currency", write_only=True
    )
    target_currency_id = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.all(), source="target_currency", write_only=True
    )

    class Meta:
        model = PriceType
        fields = [
            "id", "category", "name", "slug", "source_currency", "target_currency",
            "source_currency_id", "target_currency_id",
            "trade_type", "description", "is_active", "order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "category", "slug", "created_at", "updated_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        category = attrs.get("category")
        view = self.context.get("view")

        if not category and view is not None:
            category_pk = view.kwargs.get("category_pk")
            if category_pk:
                category = Category.objects.filter(pk=category_pk).first()
                if not category:
                    raise serializers.ValidationError({"category": ["Category not found."]})

        if not category:
            return attrs

        instance = getattr(self, "instance", None)
        name = attrs.get("name", getattr(instance, "name", None))
        qs = PriceType.objects.filter(category=category)
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)

        errors = {}
        if name and qs.filter(name=name).exists():
            errors["name"] = ["A price type with this name already exists in this category."]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class PriceTypeExplorerSerializer(serializers.ModelSerializer):
    """Nested in Category Explorer: includes latest_price from history."""
    source_currency = CurrencySerializer(read_only=True)
    target_currency = CurrencySerializer(read_only=True)
    latest_price = serializers.SerializerMethodField()
    latest_price_at = serializers.SerializerMethodField()
    change_value = serializers.SerializerMethodField()
    change_percent = serializers.SerializerMethodField()

    class Meta:
        model = PriceType
        fields = [
            "id", "name", "slug", "source_currency", "target_currency",
            "trade_type", "is_active", "order",
            "latest_price", "latest_price_at", "change_value", "change_percent",
        ]

    def _get_recent_histories(self, obj):
        histories = getattr(obj, "_latest_histories", None)
        if histories is not None:
            return histories
        if hasattr(obj, "price_histories"):
            return list(obj.price_histories.all()[:2])
        return []

    def get_latest_price(self, obj):
        histories = self._get_recent_histories(obj)
        first = histories[0] if histories else None
        if not first or first.price is None:
            return None
        return _json_safe_api_float(first.price)

    def get_latest_price_at(self, obj):
        histories = self._get_recent_histories(obj)
        first = histories[0] if histories else None
        return first.created_at if first else None

    def get_change_value(self, obj):
        histories = self._get_recent_histories(obj)
        if len(histories) < 2:
            return None
        latest = histories[0].price
        previous = histories[1].price
        if latest is None or previous is None:
            return None
        try:
            delta = float(latest) - float(previous)
        except (TypeError, ValueError):
            return None
        return _json_safe_api_float(delta)

    def get_change_percent(self, obj):
        histories = self._get_recent_histories(obj)
        if len(histories) < 2:
            return None
        latest = histories[0].price
        previous = histories[1].price
        if latest is None or previous is None:
            return None
        try:
            lp = float(latest)
            pp = float(previous)
        except (TypeError, ValueError):
            return None
        if pp == 0:
            return None
        pct = ((lp - pp) / pp) * 100
        return _json_safe_api_float(pct)


class CategorySerializer(serializers.ModelSerializer):
    price_types = PriceTypeSerializer(many=True, read_only=True)
    last_used_template = serializers.SerializerMethodField()
    template_media_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "telegram_message_description", "telegram_media_url", "inline_buttons",
            "last_used_template", "template_media_url",
            "created_at", "updated_at", "price_types",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def get_last_used_template(self, obj):
        template = _resolve_preview_template(obj)
        return getattr(template, "id", None)

    def get_template_media_url(self, obj):
        template = _resolve_preview_template(obj)
        if not template or not getattr(template, "image", None):
            return ""
        try:
            return template.image.url
        except Exception:
            return ""


class CategoryExplorerSerializer(serializers.ModelSerializer):
    """List with nested price_types and latest_price for Explorer UI."""
    price_types = PriceTypeExplorerSerializer(many=True, read_only=True)
    price_type_count = serializers.SerializerMethodField()
    last_used_template = serializers.SerializerMethodField()
    template_media_url = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "name", "slug", "description",
            "telegram_message_description", "telegram_media_url", "inline_buttons",
            "last_used_template", "template_media_url",
            "created_at", "updated_at", "price_type_count", "price_types",
        ]
        read_only_fields = fields

    def get_price_type_count(self, obj):
        # The list action prefetches price_types, so .all() reads the cache and
        # costs no extra query; the manager itself has no length.
        return len(obj.price_types.all())

    def get_last_used_template(self, obj):
        template = _resolve_preview_template(obj)
        return getattr(template, "id", None)

    def get_template_media_url(self, obj):
        template = _resolve_preview_template(obj)
        if not template or not getattr(template, "image", None):
            return ""
        try:
            return template.image.url
        except Exception:
            return ""
