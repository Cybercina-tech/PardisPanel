"""
Global DRF exception handler.
Returns a consistent JSON shape: { "error": true, "message": "...", "code": "..." }
so the frontend can show a message instead of a black screen.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def _standard_error_body(message, code=None, errors=None):
    body = {"error": True, "message": message, "code": code or "error"}
    if errors:
        body["errors"] = errors
    return body


def error_response(message, code="error", status_code=status.HTTP_400_BAD_REQUEST, errors=None, extra=None):
    body = _standard_error_body(message, code, errors=errors)
    if isinstance(extra, dict):
        body.update(extra)
    return Response(body, status=status_code)


def custom_exception_handler(exc, context):
    """Handle all API exceptions with a consistent JSON format."""
    response = exception_handler(exc, context)
    if response is not None:
        # Normalize DRF exception responses to our format
        data = response.data
        errors = None
        if isinstance(data, dict):
            normalized_errors = {}
            for k, v in data.items():
                if k in {"detail", "message", "code", "error"}:
                    continue
                if isinstance(v, list):
                    normalized_errors[k] = " ".join(str(x) for x in v)
                else:
                    normalized_errors[k] = str(v)
            errors = normalized_errors or None
            if "detail" in data:
                detail = data["detail"]
                message = " ".join(detail) if isinstance(detail, list) else str(detail)
            else:
                parts = []
                for k, v in data.items():
                    if isinstance(v, list):
                        parts.append(f"{k}: {' '.join(str(x) for x in v)}")
                    else:
                        parts.append(f"{k}: {v}")
                message = "; ".join(parts) if parts else "Request failed."
        elif isinstance(data, list):
            message = " ".join(str(d) for d in data)
        else:
            message = str(data) if data else "Request failed."
        code = "validation_error"
        if response.status_code == status.HTTP_403_FORBIDDEN:
            code = "permission_denied"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            code = "authentication_failed"
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            code = "not_found"
        elif response.status_code >= 500:
            code = "server_error"
        response.data = _standard_error_body(message, code, errors=errors)
        return response

    # Unhandled exception (e.g. 500): log server-side, return generic message
    logger.exception("Unhandled exception in API: %s", exc, exc_info=True)
    return Response(
        _standard_error_body(
            "An unexpected error occurred. Please try again later.",
            "server_error",
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
