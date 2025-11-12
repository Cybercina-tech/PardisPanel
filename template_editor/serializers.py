from django.db import transaction
from rest_framework import serializers

from .models import Element, Template


class ElementSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = Element
        fields = [
            "id",
            "type",
            "content",
            "x",
            "y",
            "font_size",
            "color",
        ]


class TemplateSerializer(serializers.ModelSerializer):
    elements = ElementSerializer(many=True, required=False)

    class Meta:
        model = Template
        fields = ["id", "name", "background", "created_at", "elements"]
        read_only_fields = ["id", "created_at"]

    def update(self, instance, validated_data):
        elements_data = validated_data.pop("elements", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if elements_data is not None:
            self._sync_elements(instance, elements_data)

        return instance

    @staticmethod
    @transaction.atomic
    def _sync_elements(template: Template, elements_data):
        existing_elements = {element.id: element for element in template.elements.all()}
        received_ids = set()

        for element_data in elements_data:
            element_id = element_data.pop("id", None)

            if element_id and element_id in existing_elements:
                element = existing_elements[element_id]
                for attr, value in element_data.items():
                    setattr(element, attr, value)
                element.save()
                received_ids.add(element_id)
            else:
                Element.objects.create(template=template, **element_data)

        to_delete_ids = set(existing_elements.keys()) - received_ids
        if to_delete_ids:
            Element.objects.filter(id__in=to_delete_ids).delete()

