"""Sync logical canvas and config base dimensions from the template background image."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Template

logger = logging.getLogger(__name__)


def sync_template_dimensions_from_background(template: "Template") -> bool:
    """
    Set canvas_width, canvas_height, and config.base_width/base_height from template.image.
    Returns True if dimensions were updated.
    """
    if not template.image:
        return False
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        path = template.image.path
    except Exception:
        return False
    if not path or not Path(path).exists():
        return False
    try:
        with Image.open(path) as im:
            w, h = im.size
    except OSError as exc:
        logger.warning("Could not read template image for canvas sync: %s", exc)
        return False
    if w < 1 or h < 1:
        return False
    template.canvas_width = int(w)
    template.canvas_height = int(h)
    cfg = dict(template.config or {})
    cfg["base_width"] = int(w)
    cfg["base_height"] = int(h)
    template.config = cfg
    return True
