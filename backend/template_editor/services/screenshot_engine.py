"""
Playwright-based screenshot engine for Vue template rendering.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

from template_editor.headless_context import build_headless_context
from template_editor.models import Template
from template_editor.render_tokens import (
    issue_headless_render_token,
    store_headless_render_context,
)

logger = logging.getLogger(__name__)

_PLAYWRIGHT = None
_BROWSER = None


class ScreenshotEngineError(RuntimeError):
    """Raised when headless browser screenshot generation fails."""


def _settings_int(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def _frontend_base_url() -> str:
    return str(getattr(settings, "PLAYWRIGHT_FRONTEND_BASE_URL", "http://127.0.0.1:5250")).rstrip("/")


def _screenshot_cache_ttl() -> int:
    return _settings_int("SCREENSHOT_CACHE_TTL", 300)


def _screenshot_timeout_ms() -> int:
    return _settings_int("PLAYWRIGHT_SCREENSHOT_TIMEOUT_MS", 30_000)


def _max_concurrent() -> int:
    return max(1, _settings_int("PLAYWRIGHT_MAX_CONCURRENT", 2))


def _price_fingerprint(template: Template, dynamic_data: Dict[str, Any]) -> str:
    updated = ""
    if getattr(template, "updated_at", None):
        updated = template.updated_at.isoformat()
    payload = {
        "template_id": template.pk,
        "updated_at": updated,
        "dynamic_data": dynamic_data or {},
    }
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_key(template_id: int, fingerprint: str) -> str:
    return f"screenshot:v1:{template_id}:{fingerprint}"


def _get_cached_png(template_id: int, fingerprint: str) -> Optional[bytes]:
    cached = cache.get(_cache_key(template_id, fingerprint))
    if not cached:
        return None
    if isinstance(cached, bytes):
        return cached
    if isinstance(cached, str):
        try:
            return base64.b64decode(cached)
        except Exception:
            return None
    return None


def _set_cached_png(template_id: int, fingerprint: str, png_bytes: bytes) -> None:
    cache.set(
        _cache_key(template_id, fingerprint),
        base64.b64encode(png_bytes).decode("ascii"),
        timeout=_screenshot_cache_ttl(),
    )


@contextmanager
def redis_semaphore(name: str, limit: int, timeout: float = 60.0):
    """Distributed concurrency limiter using Django cache (Redis)."""
    slot_key = None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for idx in range(limit):
            candidate = f"{name}:slot:{idx}"
            if cache.add(candidate, "1", timeout=int(timeout) + 30):
                slot_key = candidate
                break
        if slot_key:
            break
        time.sleep(0.25)
    if not slot_key:
        raise ScreenshotEngineError(f"Screenshot concurrency limit reached ({limit})")
    try:
        yield
    finally:
        cache.delete(slot_key)


def _get_browser():
    global _PLAYWRIGHT, _BROWSER
    if _BROWSER is not None:
        return _BROWSER
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ScreenshotEngineError(
            "playwright is not installed; run: pip install playwright && playwright install chromium"
        ) from exc

    _PLAYWRIGHT = sync_playwright().start()
    _BROWSER = _PLAYWRIGHT.chromium.launch(headless=True)
    return _BROWSER


def _issue_render_url(template_id: int, dynamic_data: dict, price_items=None) -> str:
    template = Template.objects.get(pk=template_id)
    context = build_headless_context(template, dynamic_data, price_items)
    context_id = store_headless_render_context(context)
    token = issue_headless_render_token(template_id, context_id)
    return f"{_frontend_base_url()}/headless-render/{template_id}?token={token}"


def generate_template_screenshot(
    *,
    template_id: int,
    dynamic_data: dict,
    price_items: Optional[Iterable[Tuple[Any, Any]]] = None,
    output_path: Path | None = None,
) -> bytes:
    """
    Render template via headless Chromium screenshot of the Vue render route.
    Returns PNG bytes. Uses Redis cache and concurrency semaphore.
    """
    started = time.monotonic()
    template = Template.objects.get(pk=template_id)
    fingerprint = _price_fingerprint(template, dynamic_data or {})

    cached = _get_cached_png(template_id, fingerprint)
    if cached:
        logger.info(
            "screenshot cache_hit template_id=%s duration_ms=%s",
            template_id,
            int((time.monotonic() - started) * 1000),
        )
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(cached)
        return cached

    url = _issue_render_url(template_id, dynamic_data, price_items)
    png_bytes: bytes

    try:
        with redis_semaphore("playwright:render", limit=_max_concurrent(), timeout=60.0):
            browser = _get_browser()
            context = browser.new_context(
                viewport={
                    "width": max(320, int(getattr(template, "canvas_width", None) or 1080)),
                    "height": max(320, int(getattr(template, "canvas_height", None) or 1080)),
                },
                device_scale_factor=1,
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=_screenshot_timeout_ms())
                page.wait_for_selector("#render-ready", state="attached", timeout=_screenshot_timeout_ms())
                page.wait_for_timeout(150)
                locator = page.locator("#template-canvas-root")
                locator.wait_for(state="visible", timeout=_screenshot_timeout_ms())
                png_bytes = locator.screenshot(type="png")
            except Exception as exc:
                raise ScreenshotEngineError(str(exc)) from exc
            finally:
                page.close()
                context.close()
    except ScreenshotEngineError:
        raise
    except Exception as exc:
        raise ScreenshotEngineError(str(exc)) from exc

    if not png_bytes:
        raise ScreenshotEngineError("Screenshot returned empty PNG")

    _set_cached_png(template_id, fingerprint, png_bytes)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(png_bytes)

    logger.info(
        "screenshot rendered template_id=%s render_path=playwright cache_hit=false duration_ms=%s",
        template_id,
        int((time.monotonic() - started) * 1000),
    )
    return png_bytes


def shutdown_browser() -> None:
    """Release shared Playwright browser (tests / worker shutdown)."""
    global _PLAYWRIGHT, _BROWSER
    if _BROWSER is not None:
        try:
            _BROWSER.close()
        except Exception:
            pass
        _BROWSER = None
    if _PLAYWRIGHT is not None:
        try:
            _PLAYWRIGHT.stop()
        except Exception:
            pass
        _PLAYWRIGHT = None
