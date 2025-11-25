import re
from typing import Iterable, Tuple

from django.core.exceptions import ValidationError


HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
ALIGN_CHOICES = {"left", "center", "right"}


def _ensure_fields_container(config: dict) -> dict:
    if not isinstance(config, dict):
        raise ValidationError("Configuration must be a JSON object.")
    fields = config.get("fields")
    if fields is None:
        fields = {}
        config["fields"] = fields
    if not isinstance(fields, dict):
        raise ValidationError('"fields" must be a JSON object.')
    return fields


def validate_template_config(config: dict, *, image_size: Tuple[int, int] | None = None) -> list[str]:
    """Validate config structure, raising ValidationError on critical issues and returning warnings."""

    fields = _ensure_fields_container(config)
    warnings: list[str] = []

    required_numeric = ("x", "y", "size")

    for field_name, field in fields.items():
        if not isinstance(field, dict):
            raise ValidationError(f'Field "{field_name}" must be an object.')

        for key in required_numeric:
            if key not in field:
                raise ValidationError(f'Field "{field_name}" is missing "{key}".')
            if not isinstance(field[key], (int, float)):
                raise ValidationError(f'Field "{field_name}" {key} must be numeric.')
            if field[key] < 0:
                raise ValidationError(f'Field "{field_name}" {key} cannot be negative.')

        size = field.get("size", 0)
        if size < 8 or size > 240:
            raise ValidationError(f'Field "{field_name}" font size must be between 8 and 240.')

        color = field.get("color", "#000000")
        if color and not HEX_COLOR_RE.match(color.strip()):
            raise ValidationError(f'Field "{field_name}" has invalid color "{color}".')

        align = field.get("align", "left")
        if align not in ALIGN_CHOICES:
            raise ValidationError(
                f'Field "{field_name}" align "{align}" is invalid. Use left, center, or right.'
            )

        max_width = field.get("max_width")
        if max_width is not None:
            if not isinstance(max_width, (int, float)):
                raise ValidationError(f'Field "{field_name}" max_width must be numeric.')
            if max_width <= 0:
                raise ValidationError(f'Field "{field_name}" max_width must be positive.')

    warnings.extend(_detect_out_of_bounds(fields, image_size))
    warnings.extend(_detect_overlaps(fields))
    return warnings


def _detect_out_of_bounds(fields: dict, image_size: Tuple[int, int] | None) -> Iterable[str]:
    if not image_size:
        return []
    warnings = []
    width, height = image_size
    for name, field in fields.items():
        x, y = field.get("x", 0), field.get("y", 0)
        approx_width = field.get("max_width") or max(field.get("size", 0) * 6, 40)
        approx_height = field.get("size", 0) * 1.4
        if x + approx_width > width or y + approx_height > height:
            warnings.append(f'Field "{name}" appears to extend beyond the image bounds.')
    return warnings


def _detect_overlaps(fields: dict) -> Iterable[str]:
    warnings = []
    boxes: list[tuple[str, float, float, float, float]] = []
    for name, field in fields.items():
        x, y = field.get("x", 0), field.get("y", 0)
        width = field.get("max_width") or max(field.get("size", 0) * 6, 40)
        height = field.get("size", 0) * 1.4
        boxes.append((name, x, y, x + width, y + height))

    for idx, (name, left, top, right, bottom) in enumerate(boxes):
        for other_name, o_left, o_top, o_right, o_bottom in boxes[idx + 1 :]:
            if _boxes_overlap(left, top, right, bottom, o_left, o_top, o_right, o_bottom):
                warnings.append(f'Fields "{name}" and "{other_name}" might overlap.')
    return warnings


def _boxes_overlap(l1, t1, r1, b1, l2, t2, r2, b2) -> bool:
    horizontal = (l1 < r2) and (r1 > l2)
    vertical = (t1 < b2) and (b1 > t2)
    return horizontal and vertical

