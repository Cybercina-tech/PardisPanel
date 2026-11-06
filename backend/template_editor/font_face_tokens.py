"""
Time-limited signed tokens for template editor font URLs.

@font-face loads cannot send Authorization: Bearer; the SPA uses query ?t=... instead.
"""
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

SIGNER = TimestampSigner(salt="template-editor-font-face-v1")

# How long a signed URL remains valid (must match unsign in TemplateFontFileServeAPIView).
FACE_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7  # 7 days


def sign_font_face_filename(filename: str) -> str:
    if not filename:
        return ""
    return SIGNER.sign(str(filename))


def verify_font_face_token(token: str, filename: str) -> bool:
    if not token or not filename:
        return False
    try:
        value = SIGNER.unsign(token, max_age=FACE_TOKEN_MAX_AGE_SECONDS)
        return value == filename
    except (BadSignature, SignatureExpired):
        return False
