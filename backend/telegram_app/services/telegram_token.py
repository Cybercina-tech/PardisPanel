"""Validation helpers for Telegram BotFather tokens."""

from __future__ import annotations

import re

# BotFather tokens look like "<bot_id>:<secret>" where bot_id is digits and
# secret is a 35-char base64ish string (letters + digits).
_BOTFATHER_TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,}$")


def is_valid_botfather_token(token: str | None) -> bool:
    """Whether ``token`` has the shape of a real BotFather token.

    Encrypted-at-rest tokens (Fernet ``gAAAAA...``) are handled by the model's
    ``get_plain_token``; this check applies to raw user input.
    """
    if not token or not isinstance(token, str):
        return False
    return bool(_BOTFATHER_TOKEN_RE.match(token.strip()))
