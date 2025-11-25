"""
DEPRECATED: This file is kept for backward compatibility but is no longer used.
The new template system uses JSONField configuration instead of Element models.

All new code should use the Template model directly with its config JSONField.
"""
from rest_framework import serializers

# This file is deprecated - the new system doesn't use DRF serializers
# Keeping this file to avoid import errors in case any old code references it

# Old serializers that are no longer used
# The new system uses:
# - Template model with JSONField for config
# - Direct form-based editing in the frontend
# - template_editor.utils.render_template() for rendering

class ElementSerializer(serializers.Serializer):
    """DEPRECATED: Element model has been removed."""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ElementSerializer is deprecated. "
            "The new template system uses JSONField configuration instead of Element models."
        )


class TemplateSerializer(serializers.Serializer):
    """DEPRECATED: Use Template model directly with config JSONField."""
    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "TemplateSerializer is deprecated. "
            "The new template system uses direct model access with JSONField configuration."
        )
