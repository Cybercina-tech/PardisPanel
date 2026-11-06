"""
Shared upload validation using magic numbers (content-based), not just extension.
Limits: 2MB for standard images (logo, favicon, category media), 5MB for larger assets (templates).
"""
# Magic bytes for allowed image types (signature, start offset)
_IMAGE_SIGNATURES = [
    (b"\xff\xd8\xff", 0),   # JPEG
    (b"\x89PNG\r\n\x1a\n", 0),  # PNG
    (b"GIF87a", 0),
    (b"GIF89a", 0),
    (b"RIFF", 0),   # WebP has RIFF....WEBP at 0 and WEBP at 8
]
# WebP: bytes 8:12 must be b'WEBP'
_WEBP_OFFSET = 8
_WEBP_MARKER = b"WEBP"

MAX_IMAGE_SIZE = 2 * 1024 * 1024   # 2MB
MAX_ASSET_SIZE = 5 * 1024 * 1024   # 5MB (e.g. template backgrounds)


def _read_head(file_obj, size=32):
    """Read first bytes from file. Supports both file-like and UploadedFile."""
    pos = file_obj.tell()
    try:
        head = file_obj.read(size)
        return head
    finally:
        file_obj.seek(pos)


def validate_uploaded_image(file_obj, max_size=MAX_IMAGE_SIZE, allowed_extensions=None):
    """
    Validate an uploaded file by magic numbers and size.
    Raises ValueError with a user-friendly message if invalid.
    file_obj: Django UploadedFile or file-like with read() and seek().
    max_size: max size in bytes (default 2MB).
    allowed_extensions: optional set of allowed extensions e.g. {'.jpg', '.png'}; not enforced if None.
    """
    if file_obj is None:
        return
    if hasattr(file_obj, "size") and file_obj.size > max_size:
        raise ValueError(
            "File too large. Maximum size is %d MB." % (max_size // (1024 * 1024))
        )
    head = _read_head(file_obj, 24)
    if len(head) < 12:
        raise ValueError("File is too small or empty to be a valid image.")
    # Check WebP (RIFF....WEBP)
    if head[:4] == b"RIFF" and len(head) >= 12 and head[_WEBP_OFFSET : _WEBP_OFFSET + 4] == _WEBP_MARKER:
        pass  # valid
    else:
        matched = False
        for sig, offset in _IMAGE_SIGNATURES:
            if sig == b"RIFF":
                continue  # already handled
            if head[offset : offset + len(sig)] == sig:
                matched = True
                break
        if not matched:
            raise ValueError(
                "Invalid image type. Allowed: JPEG, PNG, GIF, WebP (validate by file content)."
            )
    if allowed_extensions and hasattr(file_obj, "name") and file_obj.name:
        import os
        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext not in allowed_extensions:
            raise ValueError(
                "File extension not allowed. Allowed: %s" % ", ".join(sorted(allowed_extensions))
            )


def to_persian_digits(text) -> str:
    """Replace Western digits 0-9 with Persian digits (commas/decimals unchanged)."""
    if text is None:
        return ""
    return str(text).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def format_price_display(price) -> str:
    """
    Format a numeric price with thousands separators.
    Omit fractional part when the value is a whole number (no trailing .00).
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    if price is None:
        return ""
    try:
        d = Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return str(price)
    if d == d.to_integral_value():
        return f"{int(d):,}"
    text = format(d, "f").rstrip("0").rstrip(".")
    if "." in text:
        whole, frac = text.split(".", 1)
        try:
            return f"{int(whole):,}.{frac}"
        except ValueError:
            return text
    try:
        return f"{int(d):,}"
    except ValueError:
        return str(d)
