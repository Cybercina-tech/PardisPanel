"""
DEPRECATED: This file is kept for backward compatibility but is no longer used.
The new template rendering system uses template_editor.utils.render_template() instead.

This old renderer used the Element model which has been removed.
All new code should use template_editor.utils.render_template().
"""
import logging

logger = logging.getLogger(__name__)

# This file is deprecated - use template_editor.utils.render_template() instead
# Keeping this file to avoid import errors in case any old code references it

def render_template(template, *args, **kwargs):
    """
    DEPRECATED: Use template_editor.utils.render_template() instead.
    
    This function is kept for backward compatibility but will raise an error
    to encourage migration to the new system.
    """
    raise NotImplementedError(
        "The old render_template() function is deprecated. "
        "Please use template_editor.utils.render_template() instead. "
        "The new system uses JSONField configuration instead of Element models."
    )
