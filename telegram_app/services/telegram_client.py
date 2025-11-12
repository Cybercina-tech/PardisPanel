"""
Telegram service for sending messages and media to Telegram channels.
Compatible with python-telegram-bot v20 (async).
"""
import asyncio
import logging
from typing import Any, Iterable, List, Mapping, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError, BadRequest, TimedOut, NetworkError

logger = logging.getLogger(__name__)


class TelegramService:
    """Service class for interacting with Telegram Bot API."""
    
    def __init__(self, token):
        """
        Initialize Telegram service with bot token.
        
        Args:
            token: Telegram bot token from @BotFather
        """
        if not token:
            raise ValueError("Bot token is required")
        self.token = token
        self.bot = Bot(token=token)

    @staticmethod
    def _build_inline_keyboard(buttons: Optional[Iterable[Iterable[Mapping[str, Any]]]]):
        if not buttons:
            return None

        keyboard: List[List[InlineKeyboardButton]] = []
        for row in buttons:
            button_row: List[InlineKeyboardButton] = []
            for button in row:
                text = button.get("text")
                if not text:
                    continue
                kwargs = {}
                if "url" in button:
                    kwargs["url"] = button["url"]
                elif "callback_data" in button:
                    kwargs["callback_data"] = button["callback_data"]
                elif "switch_inline_query" in button:
                    kwargs["switch_inline_query"] = button["switch_inline_query"]
                elif "switch_inline_query_current_chat" in button:
                    kwargs["switch_inline_query_current_chat"] = button[
                        "switch_inline_query_current_chat"
                    ]

                if not kwargs:
                    continue

                button_row.append(InlineKeyboardButton(text=text, **kwargs))
            if button_row:
                keyboard.append(button_row)

        if not keyboard:
            return None

        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def _send_message_async(
        self,
        chat_id,
        text,
        parse_mode="HTML",
        buttons=None,
    ):
        """
        Async helper method to send a message.
        
        Args:
            chat_id: Telegram chat ID (can be channel username or ID)
            text: Message text to send
            parse_mode: Message parse mode (HTML, Markdown, or None)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not chat_id:
            return False, "Chat ID is required"
        
        if not text or not text.strip():
            return False, "Message text cannot be empty"
        
        try:
            reply_markup = self._build_inline_keyboard(buttons)
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            logger.info(f"Message sent successfully to {chat_id}")
            return True, "Message sent successfully."
        except BadRequest as e:
            error_msg = f"Bad request: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except TimedOut as e:
            error_msg = f"Request timed out: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except TelegramError as e:
            error_msg = f"Telegram error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg

    def send_message(self, chat_id, text, parse_mode="HTML", buttons=None):
        """
        Send a text message to a Telegram chat.
        This is a synchronous wrapper for the async method.
        
        Args:
            chat_id: Telegram chat ID (can be channel username or ID)
            text: Message text to send
            parse_mode: Message parse mode (HTML, Markdown, or None)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new event loop in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            self._send_message_async(chat_id, text, parse_mode, buttons)
                        )
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._send_message_async(chat_id, text, parse_mode, buttons)
                )
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(
                self._send_message_async(chat_id, text, parse_mode, buttons)
            )

    async def _send_photo_async(
        self,
        chat_id,
        photo,
        caption=None,
        parse_mode="HTML",
        buttons=None,
    ):
        """
        Async helper method to send a photo.
        
        Args:
            chat_id: Telegram chat ID (can be channel username or ID)
            photo: Photo file (file path, file-like object, or file_id)
            caption: Optional photo caption
            parse_mode: Caption parse mode (HTML, Markdown, or None)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not chat_id:
            return False, "Chat ID is required"
        
        if not photo:
            return False, "Photo is required"
        
        try:
            reply_markup = self._build_inline_keyboard(buttons)
            await self.bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=caption,
                parse_mode=parse_mode if caption else None,
                reply_markup=reply_markup,
            )
            logger.info(f"Photo sent successfully to {chat_id}")
            return True, "Photo sent successfully."
        except BadRequest as e:
            error_msg = f"Bad request: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except TimedOut as e:
            error_msg = f"Request timed out: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except NetworkError as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except TelegramError as e:
            error_msg = f"Telegram error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            return False, error_msg

    def send_photo(self, chat_id, photo, caption=None, parse_mode="HTML", buttons=None):
        """
        Send a photo to a Telegram chat.
        This is a synchronous wrapper for the async method.
        
        Args:
            chat_id: Telegram chat ID (can be channel username or ID)
            photo: Photo file (file path, file-like object, or file_id)
            caption: Optional photo caption
            parse_mode: Caption parse mode (HTML, Markdown, or None)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, create a new event loop in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            self._send_photo_async(
                                chat_id, photo, caption, parse_mode, buttons
                            )
                        )
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._send_photo_async(chat_id, photo, caption, parse_mode, buttons)
                )
        except RuntimeError:
            # No event loop exists, create a new one
            return asyncio.run(
                self._send_photo_async(chat_id, photo, caption, parse_mode, buttons)
            )
