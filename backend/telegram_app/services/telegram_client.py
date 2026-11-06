"""
Telegram service for sending messages and media.

Uses aiogram 3 under the hood. Sync wrappers for Celery, DRF, and admin.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import io
import logging
import os
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
)
from aiogram.types import (
    BufferedInputFile,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

logger = logging.getLogger(__name__)


def resolve_proxy_url():
    """Proxy for Telegram API calls: TELEGRAM_PROXY_URL, else standard proxy env vars.

    aiogram (aiohttp) does not read ALL_PROXY/HTTPS_PROXY on its own, so a bot in
    a proxied environment silently fails to reach Telegram. Normalise the ``socks://``
    shorthand v2ray/xray clients export to the ``socks5://`` scheme aiohttp accepts.
    """
    url = (
        os.environ.get("TELEGRAM_PROXY_URL")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("ALL_PROXY")
        or os.environ.get("all_proxy")
        or ""
    ).strip()
    if not url:
        return None
    if url.startswith("socks://"):
        url = "socks5://" + url[len("socks://"):]
    return url

try:
    from setting.utils import log_telegram_event
except ImportError:
    log_telegram_event = None


def _run_coroutine_sync(make_coroutine):
    """Run an async coroutine from sync code (Celery, DRF, management command).

    ``make_coroutine`` is a zero-arg callable returning a fresh coroutine.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop_is_running = False
    else:
        loop_is_running = True

    if loop_is_running:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(make_coroutine())).result()

    return asyncio.run(make_coroutine())


def _log_event(level: str, message: str, details: dict) -> None:
    if not log_telegram_event:
        return
    try:
        log_telegram_event(level=level, message=message, details=details)
    except Exception:
        pass


class TelegramService:
    """Sync façade over aiogram.Bot for outbound Telegram Bot API calls.

    Always creates a fresh Bot for sync call sites (Celery/admin). Do not cache
    Bot across asyncio.run() calls — aiohttp sessions die with the closed loop.
    """

    def __init__(self, token: str):
        if not token:
            raise ValueError("Bot token is required")
        self.token = token
        self._proxy = resolve_proxy_url()
        # Lazy: Bot (and its aiohttp session) is only created on first use so a
        # service instance never pins an event loop or a dead session. Sessions
        # are closed after each call and the bot is dropped for the next one.
        self._bot = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            proxy = self._proxy
            self._bot = Bot(token=self.token, proxy=proxy) if proxy else Bot(token=self.token)
        return self._bot


    @staticmethod
    def _build_inline_keyboard(
        buttons: Optional[Iterable[Iterable[Mapping[str, Any]]]],
    ) -> InlineKeyboardMarkup | None:
        if not buttons:
            return None

        keyboard: List[List[InlineKeyboardButton]] = []
        for row in buttons:
            button_row: List[InlineKeyboardButton] = []
            for button in row:
                text = button.get("text")
                if not text:
                    continue
                kwargs: dict[str, Any] = {}
                if "url" in button:
                    kwargs["url"] = button["url"]
                elif "callback_data" in button:
                    kwargs["callback_data"] = str(button["callback_data"])
                else:
                    continue
                button_row.append(InlineKeyboardButton(text=str(text), **kwargs))
            if button_row:
                keyboard.append(button_row)

        if not keyboard:
            return None
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    @staticmethod
    def _build_reply_keyboard(
        buttons: Optional[Iterable[Iterable[Mapping[str, Any] | str]]],
    ) -> ReplyKeyboardMarkup | None:
        """Bottom-of-chat button panel (not inline under a message)."""
        if not buttons:
            return None
        keyboard: List[List[KeyboardButton]] = []
        for row in buttons:
            # Tolerate a flat row of dicts accidentally passed as the whole keyboard,
            # or a row that is itself a single dict / string.
            if isinstance(row, Mapping):
                row = [row]
            elif isinstance(row, str):
                row = [row]
            button_row: List[KeyboardButton] = []
            for button in row:
                if isinstance(button, str):
                    text = button
                elif isinstance(button, Mapping):
                    text = button.get("text")
                else:
                    continue
                if not text:
                    continue
                button_row.append(KeyboardButton(text=str(text)))
            if button_row:
                keyboard.append(button_row)
        if not keyboard:
            return None
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True,
            is_persistent=True,
        )

    @classmethod
    def _build_keyboard(
        cls,
        buttons: Optional[Iterable[Iterable[Mapping[str, Any]]]],
        keyboard: str | None = None,
    ):
        if not buttons:
            return None
        kind = (keyboard or "").lower()
        if kind == "reply":
            return cls._build_reply_keyboard(buttons)
        if kind == "inline":
            return cls._build_inline_keyboard(buttons)
        # Auto: URL/callback → inline (channel posts); text-only → reply panel
        for row in buttons:
            for button in row:
                if "url" in button or "callback_data" in button:
                    return cls._build_inline_keyboard(buttons)
        return cls._build_reply_keyboard(buttons)

    @staticmethod
    def _photo_input(photo):
        if isinstance(photo, (str, Path)):
            path = Path(photo)
            if path.exists():
                return FSInputFile(path)
            return str(photo)
        if isinstance(photo, (io.BytesIO, io.BufferedReader, io.BufferedIOBase)) or hasattr(
            photo, "read"
        ):
            # aiogram uploads require bytes; file-like streams must be wrapped.
            data = photo.read() if hasattr(photo, "read") else photo
            filename = getattr(photo, "name", None)
            return BufferedInputFile(data, filename=filename or "image.png")
        return photo

    async def _send_message_async(
        self,
        chat_id,
        text,
        parse_mode="HTML",
        buttons=None,
        keyboard=None,
    ):
        if not chat_id:
            return False, "Chat ID is required", None
        if not text or not str(text).strip():
            return False, "Message text cannot be empty", None

        try:
            reply_markup = self._build_keyboard(buttons, keyboard=keyboard)
            result = await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            logger.info("Message sent successfully to %s", chat_id)
            _log_event(
                "INFO",
                "Message sent to Telegram channel",
                {
                    "event": "send_message",
                    "chat_id": str(chat_id),
                    "text_length": len(text),
                    "parse_mode": parse_mode,
                    "has_buttons": bool(buttons),
                },
            )
            return True, "Message sent successfully.", getattr(result, "message_id", None)
        except TelegramBadRequest as e:
            error_msg = f"Bad request: {e}"
            logger.error(error_msg)
            _log_event(
                "ERROR",
                "Failed to send message to Telegram",
                {
                    "event": "send_message_bad_request",
                    "chat_id": str(chat_id),
                    "error": error_msg,
                },
            )
            return False, error_msg, None
        except TelegramRetryAfter as e:
            error_msg = f"Flood control: retry after {e.retry_after}s"
            logger.error(error_msg)
            return False, error_msg, None
        except TelegramNetworkError as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            _log_event(
                "ERROR",
                "Telegram network error",
                {
                    "event": "send_message_network_error",
                    "chat_id": str(chat_id),
                    "error": error_msg,
                },
            )
            return False, error_msg, None
        except TelegramAPIError as e:
            error_msg = f"Telegram error: {e}"
            logger.error(error_msg)
            _log_event(
                "ERROR",
                "Telegram API error",
                {
                    "event": "send_message_telegram_error",
                    "chat_id": str(chat_id),
                    "error": error_msg,
                },
            )
            return False, error_msg, None
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            _log_event(
                "CRITICAL",
                "Unexpected error sending Telegram message",
                {
                    "event": "send_message_unexpected_error",
                    "chat_id": str(chat_id),
                    "error": error_msg,
                },
            )
            return False, error_msg, None
        finally:
            try:
                await self.bot.session.close()
            except Exception:
                pass
            self._bot = None

    def send_message(self, chat_id, text, parse_mode="HTML", buttons=None, keyboard=None):
        """
        Send a text message.

        ``keyboard``: ``"reply"`` (bottom panel), ``"inline"``, or None (auto).

        Returns:
            tuple: (success: bool, message: str, message_id: int | None)
        """
        if not chat_id:
            return False, "Chat ID is required", None
        if not text or not str(text).strip():
            return False, "Message text cannot be empty", None
        return _run_coroutine_sync(
            lambda: self._send_message_async(
                chat_id, text, parse_mode, buttons, keyboard=keyboard
            )
        )

    async def _send_photo_async(
        self,
        chat_id,
        photo,
        caption=None,
        parse_mode="HTML",
        buttons=None,
    ):
        if not chat_id:
            return False, "Chat ID is required"
        if not photo:
            return False, "Photo is required"

        try:
            reply_markup = self._build_keyboard(buttons)
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=self._photo_input(photo),
                caption=caption,
                parse_mode=parse_mode if caption else None,
                reply_markup=reply_markup,
            )
            logger.info("Photo sent successfully to %s", chat_id)
            cap_preview = (
                (caption[:100] + "…") if caption and len(caption) > 100 else caption
            )
            _log_event(
                "INFO",
                "Photo sent to Telegram channel",
                {
                    "event": "send_photo",
                    "chat_id": str(chat_id),
                    "caption_length": len(caption) if caption else 0,
                    "caption_preview": cap_preview or None,
                    "has_buttons": bool(buttons),
                },
            )
            return True, "Photo sent successfully."
        except TelegramBadRequest as e:
            error_msg = f"Bad request: {e}"
            logger.error(error_msg)
            _log_event(
                "ERROR",
                "Failed to send photo to Telegram",
                {
                    "event": "send_photo_bad_request",
                    "chat_id": str(chat_id),
                    "error": error_msg,
                },
            )
            return False, error_msg
        except TelegramNetworkError as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            return False, error_msg
        except TelegramAPIError as e:
            error_msg = f"Telegram error: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            return False, error_msg

    def send_photo(self, chat_id, photo, caption=None, parse_mode="HTML", buttons=None):
        return _run_coroutine_sync(
            lambda: self._send_photo_async(chat_id, photo, caption, parse_mode, buttons)
        )

    async def _edit_message_text_async(
        self,
        chat_id,
        message_id,
        text,
        parse_mode="HTML",
        buttons=None,
    ):
        if not chat_id or not message_id:
            return False, "Chat ID and message ID are required"
        if not text or not str(text).strip():
            return False, "Message text cannot be empty"

        try:
            reply_markup = self._build_keyboard(buttons)
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return True, "Message edited successfully."
        except TelegramBadRequest as e:
            error_msg = str(e)
            if "message is not modified" in error_msg.lower():
                return True, "Message unchanged."
            logger.warning("edit_message_text bad request: %s", error_msg)
            return False, f"Bad request: {error_msg}"
        except TelegramAPIError as e:
            error_msg = f"Telegram error: {e}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            return False, error_msg

    def edit_message_text(
        self,
        chat_id,
        message_id,
        text,
        parse_mode="HTML",
        buttons=None,
    ):
        return _run_coroutine_sync(
            lambda: self._edit_message_text_async(
                chat_id, message_id, text, parse_mode, buttons
            )
        )

    async def _answer_callback_query_async(
        self,
        callback_query_id,
        text=None,
        show_alert=False,
    ):
        if not callback_query_id:
            return False, "Callback query ID is required"
        try:
            await self.bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=(text[:200] if text else None),
                show_alert=bool(show_alert),
            )
            return True, "Callback answered."
        except TelegramAPIError as e:
            error_msg = f"Telegram error: {e}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            return False, error_msg

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        return _run_coroutine_sync(
            lambda: self._answer_callback_query_async(
                callback_query_id, text=text, show_alert=show_alert
            )
        )

    async def _set_webhook_async(
        self, url, secret_token=None, drop_pending_updates=False, allowed_updates=None
    ):
        if not url:
            return False, "Webhook URL is required"
        try:
            kwargs: dict[str, Any] = {
                "url": url,
                "drop_pending_updates": bool(drop_pending_updates),
            }
            if secret_token:
                kwargs["secret_token"] = secret_token
            # Telegram remembers the last allowed_updates for a token, so an
            # earlier narrow call would keep my_chat_member out for good.
            if allowed_updates is not None:
                kwargs["allowed_updates"] = list(allowed_updates)
            await self.bot.set_webhook(**kwargs)
            return True, "Webhook set."
        except TelegramAPIError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("set_webhook failed: %s", e)
            return False, str(e)

    def set_webhook(
        self, url, secret_token=None, drop_pending_updates=False, allowed_updates=None
    ):
        return _run_coroutine_sync(
            lambda: self._set_webhook_async(
                url,
                secret_token=secret_token,
                drop_pending_updates=drop_pending_updates,
                allowed_updates=allowed_updates,
            )
        )

    async def _delete_webhook_async(self, drop_pending_updates=False):
        try:
            await self.bot.delete_webhook(drop_pending_updates=bool(drop_pending_updates))
            return True, "Webhook removed."
        except TelegramAPIError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("delete_webhook failed: %s", e)
            return False, str(e)

    def delete_webhook(self, drop_pending_updates=False):
        return _run_coroutine_sync(
            lambda: self._delete_webhook_async(drop_pending_updates=drop_pending_updates)
        )

    async def _get_me_async(self):
        try:
            me = await self.bot.get_me()
            info = {
                "id": me.id,
                "is_bot": bool(me.is_bot),
                "first_name": me.first_name or "",
                "username": me.username or "",
                "can_join_groups": getattr(me, "can_join_groups", None),
                "can_read_all_group_messages": getattr(
                    me, "can_read_all_group_messages", None
                ),
                "supports_inline_queries": getattr(me, "supports_inline_queries", None),
            }
            return True, info, None
        except TelegramBadRequest as e:
            error_msg = f"Bad request: {e}"
            logger.error(error_msg)
            return False, None, error_msg
        except TelegramNetworkError as e:
            error_msg = f"Network error: {e}"
            logger.error(error_msg)
            return False, None, error_msg
        except TelegramAPIError as e:
            error_msg = f"Telegram error: {e}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            logger.exception(error_msg)
            return False, None, error_msg
        finally:
            try:
                await self.bot.session.close()
            except Exception:
                pass
            self._bot = None

    def get_me(self):
        """
        Call Telegram getMe to validate the token and return bot identity.

        Returns:
            tuple: (success: bool, info: dict | None, error: str | None)
        """
        return _run_coroutine_sync(lambda: self._get_me_async())

    async def _get_chat_member_count_async(self, chat_id):
        try:
            count = await self.bot.get_chat_member_count(chat_id)
            return True, int(count), None
        except TelegramBadRequest as e:
            return False, None, f"Bad request: {e}"
        except TelegramNetworkError as e:
            return False, None, f"Network error: {e}"
        except TelegramAPIError as e:
            return False, None, f"Telegram error: {e}"
        except Exception as e:
            logger.exception("get_chat_member_count failed: %s", e)
            return False, None, str(e)
        finally:
            try:
                await self.bot.session.close()
            except Exception:
                pass
            self._bot = None

    def get_chat_member_count(self, chat_id):
        """Return subscriber count for a channel/supergroup."""
        return _run_coroutine_sync(
            lambda: self._get_chat_member_count_async(chat_id)
        )

    async def _get_chat_member_async(self, chat_id, user_id):
        try:
            member = await self.bot.get_chat_member(chat_id, user_id)
            status = getattr(member, "status", None)
            if hasattr(status, "value"):
                status = status.value
            return True, {"status": str(status)}, None
        except TelegramBadRequest as e:
            return False, None, f"Bad request: {e}"
        except TelegramNetworkError as e:
            return False, None, f"Network error: {e}"
        except TelegramAPIError as e:
            return False, None, f"Telegram error: {e}"
        except Exception as e:
            logger.exception("get_chat_member failed: %s", e)
            return False, None, str(e)
        finally:
            try:
                await self.bot.session.close()
            except Exception:
                pass
            self._bot = None

    def get_chat_member(self, chat_id, user_id):
        """Check membership/admin status of a user in a chat."""
        return _run_coroutine_sync(
            lambda: self._get_chat_member_async(chat_id, user_id)
        )

    async def aclose(self):
        if self._bot is not None:
            try:
                await self._bot.session.close()
            except Exception:
                pass
            self._bot = None
