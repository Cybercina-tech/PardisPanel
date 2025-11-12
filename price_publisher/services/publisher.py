"""High-level price publishing utilities for Telegram image posts."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Optional

from django.utils import timezone

from PIL import Image

from price_publisher.models import PriceTemplate
from price_publisher.services.image_renderer import (
    PriceEntry,
    PriceImageRenderer,
    PriceImageRenderingError,
    RenderedPriceImage,
    TemplateAssets,
)
from price_publisher.services.legacy_category_renderer import (
    render_category_board,
    supports_category,
)
from price_publisher.services.tether_renderer import (
    render_tether_board,
    supports_tether_category,
)
from telegram_app.services.telegram_client import TelegramService


class PricePublicationError(RuntimeError):
    """Raised when the price publishing pipeline fails."""


# ----------------------------------------------------------------------
# Legacy Telegram message metadata (copied from admin_finalize.py)
# ----------------------------------------------------------------------
LEGACY_FINAL_MESSAGE = (
    "💷 خرید فروش تتر و پوند نقدی و حسابی\n"
    "🔺🔺🔺🔺🔺🔺🔺🔺🔺\n"
    "Mr. Mahdi    📞  +447533544249\n\n"
    "Ms. Kianian    📞  +989121894230\n\n"
    "Manager  📞  +447399990340\n"
    "🔺🔺🔺🔺🔺🔺🔺🔺🔺\n"
    "📌آدرس دفتر :\n"
    "<u>Office A\n"
    "708A High Road\n"
    "North Finchley\n"
    "N129QL</u>\n\n"
    "🔺🔺🔺🔺🔺🔺🔺🔺🔺\n\n"
    "مبالغ زیر ۱۰۰۰ پوند شامل ۱۰ پوند کارمزد می‌باشد\n\n"
    "⛔ لطفا بدون هماهنگی هیچ مبلغی به هیچ حسابی واریز نکنید ⛔"
)

LEGACY_FINAL_BUTTONS = [
    [
        {
            "text": "ارتباط با کارشناس خرید و فروش 1",
            "url": "https://wa.me/447533544249",
        }
    ],
    [
        {
            "text": "ارتباط با کارشناس خرید و فروش 2",
            "url": "https://wa.me/989121894230",
        }
    ],
    [
        {"text": "مدیریت صرافی", "url": "https://wa.me/447399990340"},
    ],
    [
        {"text": "وب سایت", "url": "https://sarafipardis.co.uk/"},
        {
            "text": "اینستاگرام",
            "url": "https://www.instagram.com/sarafiipardis",
        },
    ],
    [
        {"text": "کانال تلگرام ما", "url": "https://t.me/sarafipardis"},
        {"text": "بات تلگرامی ما", "url": "https://t.me/PardisSarafiBot"},
    ],
]


@dataclass(frozen=True)
class PublicationResult:
    """Outcome of a Telegram publication request."""

    success: bool
    response: str
    caption: Optional[str]


class PricePublisherService:
    """Coordinates rendering price cards and sending them to Telegram."""

    def __init__(self, renderer: Optional[PriceImageRenderer] = None) -> None:
        self._renderer = renderer or PriceImageRenderer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def publish_category_prices(
        self,
        *,
        category,
        price_items: Iterable[tuple],
        channel,
        notes: Optional[str] = None,
    ) -> PublicationResult:
        """Render and post category prices to Telegram.

        Args:
            category: `category.models.Category` instance the prices belong to.
            price_items: Iterable of `(price_type, price_history)` tuples.
            channel: `telegram_app.models.TelegramChannel` destination.
            notes: Optional additional text to show on the image footer.
        """

        entries = []
        latest_timestamp = None

        for price_type, price_history in price_items:
            subtitle = self._build_pricetype_subtitle(price_type)
            meta = self._build_price_meta(price_history)
            entries.append(
                PriceEntry(
                    title=price_type.name,
                    price=self._format_price(price_history.price),
                    subtitle=subtitle,
                    meta=meta,
                )
            )

            history_timestamp = self._get_history_timestamp(price_history)
            if latest_timestamp is None or history_timestamp > latest_timestamp:
                latest_timestamp = history_timestamp

        if not entries:
            raise PricePublicationError("No price entries were provided for publication.")

        template = self._get_template_for_category(category)
        template_assets = self._build_template_assets(template)

        image = self._render_category_image(
            category=category,
            price_items=price_items,
            category_name=category.name,
            entries=entries,
            notes=notes,
            timestamp=latest_timestamp,
            template_assets=template_assets,
        )

        caption = LEGACY_FINAL_MESSAGE
        return self._send_photo(
            channel=channel,
            image=image,
            caption=caption,
            buttons=LEGACY_FINAL_BUTTONS,
        )

    def publish_special_price(
        self,
        *,
        special_price_type,
        price_history,
        channel,
        notes: Optional[str] = None,
    ) -> PublicationResult:
        """Render and post a special price to Telegram."""

        subtitle = self._build_pricetype_subtitle(special_price_type)

        entry = PriceEntry(
            title=special_price_type.name,
            price=self._format_price(price_history.price),
            subtitle=subtitle,
            meta=self._build_price_meta(price_history),
        )

        template = self._get_template_for_special(special_price_type)
        template_assets = self._build_template_assets(template)

        image = self._render_special_price_image(
            title=f"Special Price: {special_price_type.name}",
            entry=entry,
            notes=notes or price_history.notes,
            timestamp=self._get_history_timestamp(price_history),
            template_assets=template_assets,
        )

        caption = f"Special price • {special_price_type.name}"
        return self._send_photo(
            channel=channel,
            image=image,
            caption=LEGACY_FINAL_MESSAGE,
            buttons=LEGACY_FINAL_BUTTONS,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _render_category_image(
        self,
        *,
        category,
        price_items,
        category_name: str,
        entries: list[PriceEntry],
        notes: Optional[str],
        timestamp,
        template_assets: Optional[TemplateAssets],
    ) -> RenderedPriceImage:
        if supports_tether_category(category):
            try:
                return render_tether_board(
                    category=category,
                    price_items=price_items,
                    timestamp=timestamp,
                )
            except FileNotFoundError as exc:
                raise PricePublicationError(str(exc)) from exc

        if supports_category(category):
            try:
                return render_category_board(
                    category=category,
                    price_items=price_items,
                    timestamp=timestamp,
                )
            except FileNotFoundError as exc:
                raise PricePublicationError(str(exc)) from exc

        try:
            return self._renderer.render_category_prices(
                category_name=category_name,
                price_entries=entries,
                notes=notes,
                timestamp=timestamp,
                template_assets=template_assets,
            )
        except PriceImageRenderingError as exc:  # pragma: no cover - delegated
            raise PricePublicationError(str(exc)) from exc

    def _render_special_price_image(
        self,
        *,
        title: str,
        entry: PriceEntry,
        notes: Optional[str],
        timestamp,
        template_assets: Optional[TemplateAssets],
    ) -> RenderedPriceImage:
        try:
            return self._renderer.render_special_price(
                title=title,
                price_entry=entry,
                notes=notes,
                timestamp=timestamp,
                template_assets=template_assets,
            )
        except PriceImageRenderingError as exc:  # pragma: no cover - delegated
            raise PricePublicationError(str(exc)) from exc

    def _send_photo(
        self,
        *,
        channel,
        image: RenderedPriceImage,
        caption: Optional[str],
        buttons: Optional[list[list[dict]]] = None,
    ) -> PublicationResult:
        stream = self._prepare_stream(image.stream, fallback_name="prices.png")

        service = TelegramService(channel.bot.token)
        success, response = service.send_photo(
            channel.chat_id,
            stream,
            caption=caption,
            buttons=buttons,
        )

        return PublicationResult(success=success, response=response, caption=caption)

    @staticmethod
    def _build_pricetype_subtitle(price_type) -> str:
        source_code = getattr(price_type.source_currency, "code", "-")
        target_code = getattr(price_type.target_currency, "code", "-")
        trade_display = getattr(price_type, "get_trade_type_display", None)
        if callable(trade_display):
            trade_label = trade_display()
        else:
            trade_label = getattr(price_type, "trade_type", "")

        normalized_trade = trade_label.capitalize() if isinstance(trade_label, str) else ""
        pair = f"{source_code}/{target_code}"
        return f"{pair} • {normalized_trade}".strip(" •")

    @staticmethod
    def _build_price_meta(price_history) -> Optional[str]:
        pieces = []

        updated_at = getattr(price_history, "updated_at", None) or getattr(
            price_history, "created_at", None
        )
        if updated_at:
            localized = timezone.localtime(updated_at)
            pieces.append(localized.strftime("Updated %Y-%m-%d %H:%M"))

        notes = getattr(price_history, "notes", None)
        if notes:
            pieces.append(notes)

        return " • ".join(pieces) if pieces else None

    @staticmethod
    def _format_price(price) -> str:
        return f"{price:,.2f}"

    @staticmethod
    def _prepare_stream(stream: io.BytesIO, fallback_name: str) -> io.BytesIO:
        if not getattr(stream, "name", None):
            stream.name = fallback_name
        stream.seek(0)
        return stream

    @staticmethod
    def _get_history_timestamp(price_history):
        timestamp = getattr(price_history, "updated_at", None) or getattr(
            price_history, "created_at", None
        )
        return timestamp or timezone.now()

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------
    def _get_template_for_category(self, category):
        if not category:
            return self._get_default_template()

        template = (
            PriceTemplate.objects.filter(
                template_type=PriceTemplate.TemplateType.CATEGORY,
                category=category,
                is_active=True,
            )
            .select_related("category")
            .first()
        )

        if template:
            return template

        return self._get_default_template()

    def _get_template_for_special(self, special_price_type):
        if not special_price_type:
            return self._get_default_template()

        template = (
            PriceTemplate.objects.filter(
                template_type=PriceTemplate.TemplateType.SPECIAL,
                special_price_type=special_price_type,
                is_active=True,
            )
            .select_related("special_price_type")
            .first()
        )

        if template:
            return template

        return self._get_default_template()

    def _get_default_template(self):
        return (
            PriceTemplate.objects.filter(
                template_type=PriceTemplate.TemplateType.DEFAULT,
                is_active=True,
            )
            .order_by("name")
            .first()
        )

    def _build_template_assets(self, template: Optional[PriceTemplate]) -> Optional[TemplateAssets]:
        if not template:
            return None

        background_image = self._open_image_field(template.background_image)
        if background_image is None:
            return None

        logo_image = self._open_image_field(template.logo_image)
        watermark_image = self._open_image_field(template.watermark_image)

        return TemplateAssets(
            background=background_image,
            logo=logo_image,
            watermark=watermark_image,
        )

    def _open_image_field(self, field) -> Optional[Image.Image]:
        if not field:
            return None

        try:
            with field.open("rb") as file_obj:
                image = Image.open(file_obj)
                converted = image.convert("RGBA")
                converted.load()
                return converted
        except FileNotFoundError:
            return None
        except Exception as exc:  # pragma: no cover - defensive
            raise PricePublicationError(f"Failed to load template image: {exc}") from exc



