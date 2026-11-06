from rest_framework import serializers

from core.utils import validate_uploaded_image, MAX_ASSET_SIZE
from .models import PriceTemplate


class PriceTemplateSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    special_price_type_name = serializers.CharField(
        source="special_price_type.name", read_only=True, default=None
    )

    class Meta:
        model = PriceTemplate
        fields = [
            "id",
            "name",
            "template_type",
            "category",
            "category_name",
            "special_price_type",
            "special_price_type_name",
            "background_image",
            "logo_image",
            "watermark_image",
            "is_active",
            "plan",
            "notes",
            "created_at",
            "updated_at",
        ]

    def _validate_image_field(self, value):
        if value and hasattr(value, "read"):
            try:
                validate_uploaded_image(value, max_size=MAX_ASSET_SIZE)
            except ValueError as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate_background_image(self, value):
        return self._validate_image_field(value)

    def validate_logo_image(self, value):
        return self._validate_image_field(value)

    def validate_watermark_image(self, value):
        return self._validate_image_field(value)

    def validate_plan(self, value):
        from accounts.plans import can_assign_template_plan

        request = self.context.get("request")
        if not can_assign_template_plan(request):
            raise serializers.ValidationError("Only programmers can assign template plans.")
        return value
