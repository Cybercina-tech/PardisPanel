"""High-level price publishing utilities for Telegram image posts."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Optional

from django.utils import timezone
import jdatetime

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
from price_publisher.services.special_offer_renderer import (
    SPECIAL_GBP_TEMPLATES,
    normalize_identifier,
    render_special_offer_board,
    resolve_special_offer_template,
    supports_special_offer_type,
)
from telegram_app.services.telegram_client import TelegramService


class PricePublicationError(RuntimeError):
    """Raised when the price publishing pipeline fails."""


# ----------------------------------------------------------------------
# Constants for special GBP template detection
# ----------------------------------------------------------------------
SPECIAL_GBP_KEYWORDS = {
    # Buy cash keywords
    "خریدنقدیپوندویژه", "خریدویژهنقدیپوند", "خریدویژهنقدی",
    "buycashpoundspecial", "specialbuycashgbp", "special_buy_cash_gbp",
    "buycashgbpspecial", "buycashspecial", "specialcashpurchase",
    # Buy account keywords
    "خریدویژهازحساب",
    "buyaccountspecial", "specialbuyaccountgbp", "special_buy_account_gbp", "buyaccountgbpspecial",
    # Sell cash keywords
    "فروشویژهنقدی",
    "sellcashspecial", "specialselcashgbp", "special_sell_cash_gbp", "sellcashgbpspecial",
    # Sell account keywords
    "فروشویژهازحساب",
    "sellaccountspecial", "specialselaccountgbp", "special_sell_account_gbp", "sellaccountgbpspecial",
}

BUY_ACCOUNT_KEYWORDS = {
    "خریدویژهازحساب", "buyaccountspecial", "specialbuyaccountgbp",
    "special_buy_account_gbp", "buyaccountgbpspecial",
}

SELL_CASH_KEYWORDS = {
    "فروشویژهنقدی", "sellcashspecial", "specialselcashgbp",
    "special_sell_cash_gbp", "sellcashgbpspecial",
}

SELL_ACCOUNT_KEYWORDS = {
    "فروشویژهازحساب", "sellaccountspecial", "specialselaccountgbp",
    "special_sell_account_gbp", "sellaccountgbpspecial",
}

# Template to type mapping
TEMPLATE_TYPE_MAP = {
    "special_buy_account_GBP.jpg": (True, False),   # (is_account, is_sell)
    "special_sell_cash_GBP.jpg": (False, True),
    "special_sell_account_GBP.jpg": (True, True),
}

# Persian date constants
FARSI_MONTHS = [
    "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]

FARSI_WEEKDAYS = {
    "Saturday": "شنبه",
    "Sunday": "یکشنبه",
    "Monday": "دوشنبه",
    "Tuesday": "سه‌شنبه",
    "Wednesday": "چهارشنبه",
    "Thursday": "پنجشنبه",
    "Friday": "جمعه",
}

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Contact information
CONTACT_INFO = {
    "Mr. Mahdi": "+447533544249",
    "Ms. Kianian": "+989121894230",
    "Manager": "+447399990340",
}

OFFICE_ADDRESS = """Office A
708A High Road
North Finchley
N129QL"""

# ----------------------------------------------------------------------
# Legacy Telegram message metadata (copied from admin_finalize.py)
# ----------------------------------------------------------------------
LEGACY_FINAL_MESSAGE = (
    "💷 <b>خرید فروش تتر و پوند نقدی و حسابی</b>\n\n"
    "📱 <a href=\"https://wa.me/447533544249\">+447533544249</a>\n\n"
    "📍 <b>آدرس دفتر:</b>\n"
    "<a href=\"https://maps.app.goo.gl/d3sorvbK9VRFvSBaA\">Office A\n"
    "708A High Road\n"
    "North Finchley\n"
    "N129QL</a>\n\n"
    "🕐 <b>ساعات کاری:</b>\n"
    "دوشنبه تا شنبه: 9:30 صبح تا ۱۷\n"
    "یکشنبه ها: تعطیل"
)

LEGACY_FINAL_BUTTONS = [
    [
        {
            "text": "ارتباط با امور مشتریان ۱",
            "url": "https://wa.me/447533544249",
        }
    ],
    [
        {
            "text": "ارتباط با امور مشتریان ۲",
            "url": "https://wa.me/989121894230",
        }
    ],
    [
        {"text": "ارتباط با امور مشتریان ۳", "url": "https://wa.me/447399990340"},
    ],
    [
        {"text": "وب سایت", "url": "https://sarafipardis.co.uk/"},
        {
            "text": "اینستاگرام",
            "url": "https://www.instagram.com/sarafiipardis",
        },
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

        # Use professional caption for Tether and GBP categories
        if supports_tether_category(category):
            caption = self._build_tether_caption(latest_timestamp)
        elif supports_category(category):
            caption = self._build_gbp_category_caption(latest_timestamp)
        else:
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

        custom_offer = supports_special_offer_type(special_price_type)
        if custom_offer:
            try:
                image = render_special_offer_board(
                    special_price_type=special_price_type,
                    price_history=price_history,
                )
            except FileNotFoundError as exc:
                raise PricePublicationError(str(exc)) from exc
        else:
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

        # Build caption for special GBP offers (inspired by Tether)
        caption = self._build_special_price_caption(special_price_type, price_history, custom_offer)
            
        return self._send_photo(
            channel=channel,
            image=image,
            caption=caption,
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

    def _build_special_price_caption(self, special_price_type, price_history, custom_offer: bool) -> str:
        """Build caption for special price offers, detecting if it's a special GBP template."""
        special_price_name = getattr(special_price_type, "name", "")
        normalized_name = normalize_identifier(special_price_name)
        
        # Check if it's a special GBP template
        template = resolve_special_offer_template(special_price_type) if custom_offer else None
        is_special_gbp = (
            template is not None 
            and template.background in SPECIAL_GBP_TEMPLATES
        ) or any(keyword in normalized_name for keyword in SPECIAL_GBP_KEYWORDS)
        
        if not is_special_gbp:
            return LEGACY_FINAL_MESSAGE
        
        # Determine template type (account/sell flags)
        is_account, is_sell = self._detect_template_type(template, normalized_name)
        
        timestamp = self._get_history_timestamp(price_history)
        return self._build_special_pound_caption(timestamp, is_account=is_account, is_sell=is_sell)
    
    def _detect_template_type(self, template, normalized_name: str) -> tuple[bool, bool]:
        """Detect if template is account-based and/or sell type. Returns (is_account, is_sell)."""
        # First check template background
        if template and template.background in TEMPLATE_TYPE_MAP:
            return TEMPLATE_TYPE_MAP[template.background]
        
        # Fallback to keyword matching
        if any(keyword in normalized_name for keyword in SELL_ACCOUNT_KEYWORDS):
            return (True, True)  # Sell account
        if any(keyword in normalized_name for keyword in BUY_ACCOUNT_KEYWORDS):
            return (True, False)  # Buy account
        if any(keyword in normalized_name for keyword in SELL_CASH_KEYWORDS):
            return (False, True)  # Sell cash
        
        return (False, False)  # Default: Buy cash
    
    @staticmethod
    def _format_dates(timestamp) -> tuple[str, str, str, str]:
        """Format Persian and English dates from timestamp. Returns (farsi_date, farsi_weekday, english_date, english_weekday)."""
        now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
        jalali = jdatetime.datetime.fromgregorian(datetime=now)
        
        farsi_date = f"{jalali.day} {FARSI_MONTHS[jalali.month]} {jalali.year}"
        farsi_weekday = FARSI_WEEKDAYS.get(now.strftime("%A"), "")
        # Format English date with zero-padded day: "December 04, 2025"
        english_date = now.strftime("%B %d, %Y")
        english_weekday = now.strftime("%A")
        
        # Convert English digits to Persian
        farsi_date = farsi_date.translate(PERSIAN_DIGITS)
        
        return farsi_date, farsi_weekday, english_date, english_weekday
    
    @staticmethod
    def _build_contact_section() -> str:
        """Build the contact information section of the caption."""
        mahdi_phone = "+447533544249"
        whatsapp_link = f"https://wa.me/{mahdi_phone.replace('+', '')}"
        return f"📱 <a href=\"{whatsapp_link}\">{mahdi_phone}</a>"
    
    @staticmethod
    def _build_common_description(title: str) -> str:
        """Build common description section in Tether style (without dates)."""
        contact_section = PricePublisherService._build_contact_section()
        office_map_url = "https://maps.app.goo.gl/d3sorvbK9VRFvSBaA"
        
        if title:
            caption = (
                f"💷 <b>{title}</b>\n\n"
                f"{contact_section}\n\n"
                f"📍 <b>آدرس دفتر:</b>\n"
                f"<a href=\"{office_map_url}\">{OFFICE_ADDRESS}</a>\n\n"
                f"🕐 <b>ساعات کاری:</b>\n"
                f"دوشنبه تا شنبه: 9:30 صبح تا ۱۷\n"
                f"یکشنبه ها: تعطیل"
            )
        else:
            # Return only description part without title
            caption = (
                f"{contact_section}\n\n"
                f"📍 <b>آدرس دفتر:</b>\n"
                f"<a href=\"{office_map_url}\">{OFFICE_ADDRESS}</a>\n\n"
                f"🕐 <b>ساعات کاری:</b>\n"
                f"دوشنبه تا شنبه: 9:30 صبح تا ۱۷\n"
                f"یکشنبه ها: تعطیل"
            )
        
        return caption
    
    @staticmethod
    def _build_tether_caption(timestamp) -> str:
        """Build a professional and attractive caption for Tether prices with dates."""
        farsi_date, farsi_weekday, english_date, english_weekday = PricePublisherService._format_dates(timestamp)
        
        caption = (
            f"📅 <b>تاریخ:</b>\n\n"
            f"🇮🇷 {farsi_weekday} {farsi_date}\n\n"
            f"🇬🇧 {english_weekday}, {english_date}\n\n"
            f"━━━━━━\n\n"
            f"{PricePublisherService._build_common_description('خرید فروش تتر')}"
        )
        
        return caption
    
    @staticmethod
    def _build_gbp_category_caption(timestamp) -> str:
        """Build a professional and attractive caption for GBP category prices without dates."""
        return PricePublisherService._build_common_description('خرید فروش پوند')

    @staticmethod
    def _get_special_pound_title(is_account: bool, is_sell: bool) -> str:
        """Get the title for special pound caption based on type."""
        if is_sell and is_account:
            return "💷 <b>فروش ویژه از حساب پوند</b>"
        elif is_sell:
            return "💷 <b>فروش ویژه نقدی پوند</b>"
        elif is_account:
            return "💷 <b>خرید ویژه از حساب پوند</b>"
        else:
            return "💷 <b>خرید ویژه نقدی پوند</b>"
    
    @staticmethod
    def _build_special_pound_caption(timestamp, is_account: bool = False, is_sell: bool = False) -> str:
        """Build a professional and attractive caption for Special Pound prices without dates."""
        title = PricePublisherService._get_special_pound_title(is_account, is_sell)
        
        # Get description without title
        description = PricePublisherService._build_common_description('')
        
        caption = (
            f"{title}\n\n"
            f"{description}"
        )
        
        return caption



