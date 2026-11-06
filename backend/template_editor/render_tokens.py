"""
Time-limited signed tokens for headless Vue template rendering (Playwright).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict

from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

SIGNER = TimestampSigner(salt="headless-render-v1")
TOKEN_MAX_AGE_SECONDS = 120
CONTEXT_CACHE_PREFIX = "headless_render:ctx:"
CONTEXT_CACHE_TTL = 120


def _context_cache_key(context_id: str) -> str:
    return f"{CONTEXT_CACHE_PREFIX}{context_id}"


def store_headless_render_context(context: Dict[str, Any]) -> str:
    """Persist render context in Redis and return opaque context_id."""
    context_id = uuid.uuid4().hex
    cache.set(_context_cache_key(context_id), context, timeout=CONTEXT_CACHE_TTL)
    return context_id


def load_headless_render_context(context_id: str) -> Dict[str, Any] | None:
    if not context_id:
        return None
    payload = cache.get(_context_cache_key(context_id))
    if not isinstance(payload, dict):
        return None
    return payload


def issue_headless_render_token(template_id: int, context_id: str) -> str:
    """Return signed token embedding template_id and context_id."""
    payload = f"{int(template_id)}:{context_id}"
    return SIGNER.sign(payload)


def verify_headless_render_token(token: str) -> Dict[str, Any]:
    """
    Validate token and return {template_id, context_id}.
    Raises ValueError on invalid/expired token.
    """
    if not token:
        raise ValueError("Missing token")
    try:
        raw = SIGNER.unsign(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except SignatureExpired as exc:
        raise ValueError("Render token expired") from exc
    except BadSignature as exc:
        raise ValueError("Invalid render token") from exc

    parts = str(raw).split(":", 1)
    if len(parts) != 2:
        raise ValueError("Malformed render token")
    try:
        template_id = int(parts[0])
    except (TypeError, ValueError) as exc:
        raise ValueError("Malformed render token") from exc
    context_id = parts[1].strip()
    if not context_id:
        raise ValueError("Malformed render token")
    return {"template_id": template_id, "context_id": context_id}
