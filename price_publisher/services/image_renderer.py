from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Union

from django.conf import settings
from django.utils import timezone

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
except ImportError as exc:  # pragma: no cover - Pillow is a hard dependency for this module
    raise RuntimeError(
        "Pillow is required to render price images. Install it via `pip install Pillow`."
    ) from exc


FontType = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


class PriceImageRenderingError(RuntimeError):
    """Raised when the renderer fails to create the price image."""


@dataclass(frozen=True)
class PriceEntry:
    """Container describing a single price entry for rendering."""

    title: str
    price: str
    subtitle: Optional[str] = None
    meta: Optional[str] = None


@dataclass(frozen=True)
class RenderedPriceImage:
    """Result of the rendering process."""

    stream: io.BytesIO
    width: int
    height: int


@dataclass(frozen=True)
class TemplateAssets:
    """Optional assets that customise the rendered image."""

    background: Optional[Image.Image] = None
    logo: Optional[Image.Image] = None
    watermark: Optional[Image.Image] = None


class PriceImageRenderer:
    """Render category and special prices into branded PNG images."""

    DEFAULT_WIDTH = 1080
    PADDING = 80
    HEADER_GAP = 40
    ROW_HEIGHT = 150
    ROW_GAP = 24
    FOOTER_GAP = 36

    BACKGROUND_COLOUR = (17, 20, 36)
    BACKGROUND_OVERLAY = (38, 86, 216, 35)  # semi-transparent blue overlay
    CARD_COLOUR = (28, 34, 62)
    CARD_HIGHLIGHT = (62, 94, 196)
    TEXT_PRIMARY = (236, 240, 255)
    TEXT_SECONDARY = (176, 184, 214)
    TEXT_ACCENT = (88, 166, 255)

    HEADER_FONT_SIZE = 70
    SUBHEADER_FONT_SIZE = 36
    PRICE_FONT_SIZE = 54
    BODY_FONT_SIZE = 34
    FOOTER_FONT_SIZE = 30

    FONT_DIR = Path(getattr(settings, "PRICE_RENDERER_FONT_ROOT", Path("static") / "fonts"))
    FONT_REGULAR = "Roboto-Regular.ttf"
    FONT_BOLD = "Roboto-Bold.ttf"

    def __init__(
        self,
        *,
        width: int = DEFAULT_WIDTH,
        regular_font_path: Optional[Path] = None,
        bold_font_path: Optional[Path] = None,
    ) -> None:
        self.width = width

        self._font_regular = self._load_font(
            regular_font_path, self.FONT_REGULAR, self.BODY_FONT_SIZE
        )
        self._font_bold = self._load_font(
            bold_font_path, self.FONT_BOLD, self.BODY_FONT_SIZE
        )

        # Derive scaled fonts from base ones
        self._font_header = self._derive_font(self._font_bold, self.HEADER_FONT_SIZE)
        self._font_subheader = self._derive_font(
            self._font_regular, self.SUBHEADER_FONT_SIZE
        )
        self._font_price = self._derive_font(self._font_bold, self.PRICE_FONT_SIZE)
        self._font_body = self._derive_font(self._font_regular, self.BODY_FONT_SIZE)
        self._font_footer = self._derive_font(self._font_regular, self.FOOTER_FONT_SIZE)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def render_category_prices(
        self,
        *,
        category_name: str,
        price_entries: Iterable[PriceEntry],
        notes: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        template_assets: Optional[TemplateAssets] = None,
    ) -> RenderedPriceImage:
        """Render a category price card."""

        entries = list(price_entries)
        if not entries:
            raise PriceImageRenderingError("No prices provided for rendering.")

        footer_text = self._build_footer(timestamp)
        return self._render_image(
            header_text=f"{category_name} – Updated Prices",
            entries=entries,
            notes=notes,
            footer_text=footer_text,
            template_assets=template_assets,
        )

    def render_special_price(
        self,
        *,
        title: str,
        price_entry: PriceEntry,
        notes: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        template_assets: Optional[TemplateAssets] = None,
    ) -> RenderedPriceImage:
        """Render a single special price card."""

        footer_text = self._build_footer(timestamp)
        return self._render_image(
            header_text=title,
            entries=[price_entry],
            notes=notes,
            footer_text=footer_text,
            template_assets=template_assets,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _render_image(
        self,
        *,
        header_text: str,
        entries: list[PriceEntry],
        notes: Optional[str],
        footer_text: Optional[str],
        template_assets: Optional[TemplateAssets] = None,
    ) -> RenderedPriceImage:
        try:
            line_height_body = self._line_height(self._font_body)
            header_height = self._line_height(self._font_header)
            notes_height = 0

            if notes:
                wrapped_notes = self._wrap_text(
                    notes,
                    font=self._font_body,
                    max_width=self.width - 2 * self.PADDING,
                )
                notes_height = len(wrapped_notes) * line_height_body + self.FOOTER_GAP
            else:
                wrapped_notes = []

            footer_height = (self._line_height(self._font_footer) + self.FOOTER_GAP)
            total_rows_height = (
                len(entries) * self.ROW_HEIGHT + max(len(entries) - 1, 0) * self.ROW_GAP
            )

            height = (
                self.PADDING
                + header_height
                + self.HEADER_GAP
                + total_rows_height
                + notes_height
                + footer_height
                + self.PADDING
            )

            background_image = template_assets.background if template_assets else None

            if background_image:
                fitted = ImageOps.fit(
                    background_image,
                    (self.width, height),
                    method=Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS,
                )
                image = fitted.convert("RGBA")
            else:
                image = Image.new("RGBA", (self.width, height), self.BACKGROUND_COLOUR)

            draw = ImageDraw.Draw(image)

            # Add overlay for subtle gradient if using default background
            if not background_image:
                overlay = Image.new("RGBA", image.size, self.BACKGROUND_OVERLAY)
                overlay = overlay.filter(ImageFilter.GaussianBlur(radius=60))
                image = Image.alpha_composite(image, overlay)
                draw = ImageDraw.Draw(image)

            y = self.PADDING

            # Header
            draw.text(
                (self.PADDING, y),
                header_text,
                font=self._font_header,
                fill=self.TEXT_ACCENT,
            )
            y += header_height + self.HEADER_GAP

            # Entries
            for idx, entry in enumerate(entries):
                card_top = y
                card_bottom = card_top + self.ROW_HEIGHT
                card_left = self.PADDING
                card_right = self.width - self.PADDING

                self._draw_card(
                    draw,
                    image,
                    (card_left, card_top, card_right, card_bottom),
                    entry=entry,
                )

                y = card_bottom + self.ROW_GAP

            # Notes (if any)
            if wrapped_notes:
                y += max(self.ROW_GAP - self.FOOTER_GAP, 0)
                for line in wrapped_notes:
                    draw.text(
                        (self.PADDING, y),
                        line,
                        font=self._font_body,
                        fill=self.TEXT_SECONDARY,
                    )
                    y += line_height_body
                y += self.FOOTER_GAP

            # Footer / timestamp
            if footer_text:
                draw.text(
                    (self.PADDING, height - self.PADDING - self._line_height(self._font_footer)),
                    footer_text,
                    font=self._font_footer,
                    fill=self.TEXT_SECONDARY,
                )

            # Place logo if provided
            if template_assets and template_assets.logo:
                logo = template_assets.logo.convert("RGBA")
                max_width = int(self.width * 0.22)
                scaling_factor = min(1.0, max_width / logo.width)
                if scaling_factor < 1.0:
                    new_size = (
                        int(logo.width * scaling_factor),
                        int(logo.height * scaling_factor),
                    )
                    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                    logo = logo.resize(new_size, resample)

                position = (
                    self.width - self.PADDING - logo.width,
                    self.PADDING - int(self.PADDING * 0.4),
                )
                image.paste(logo, position, logo)

            # Place watermark if provided
            if template_assets and template_assets.watermark:
                watermark = template_assets.watermark.convert("RGBA")
                max_width = int(self.width * 0.3)
                scaling_factor = min(1.0, max_width / watermark.width)
                if scaling_factor < 1.0:
                    new_size = (
                        int(watermark.width * scaling_factor),
                        int(watermark.height * scaling_factor),
                    )
                    resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                    watermark = watermark.resize(new_size, resample)

                position = (
                    self.width - self.PADDING - watermark.width,
                    height - self.PADDING - watermark.height,
                )
                image.paste(watermark, position, watermark)

            # Convert to BytesIO
            rgb_image = image.convert("RGB")  # Telegram prefers JPEG/PNG without alpha
            stream = io.BytesIO()
            rgb_image.save(stream, format="PNG", optimize=True)
            stream.seek(0)

            return RenderedPriceImage(stream=stream, width=self.width, height=height)

        except Exception as exc:  # pragma: no cover - defensive programming
            raise PriceImageRenderingError("Failed to render price image") from exc

    def _draw_card(
        self,
        draw: ImageDraw.ImageDraw,
        image: Image.Image,
        box: tuple[int, int, int, int],
        *,
        entry: PriceEntry,
    ) -> None:
        left, top, right, bottom = box

        draw.rounded_rectangle(
            box,
            radius=36,
            fill=self.CARD_COLOUR,
            outline=self.CARD_HIGHLIGHT,
            width=2,
        )

        inner_padding_x = 36
        inner_padding_y = 28

        # Title & price
        current_y = top + inner_padding_y

        draw.text(
            (left + inner_padding_x, current_y),
            entry.title,
            font=self._font_bold,
            fill=self.TEXT_PRIMARY,
        )

        price_text = entry.price
        price_bbox = draw.textbbox((0, 0), price_text, font=self._font_price)
        price_width = price_bbox[2] - price_bbox[0]
        price_height = price_bbox[3] - price_bbox[1]

        price_x = right - inner_padding_x - price_width
        price_y = top + (self.ROW_HEIGHT - price_height) / 2

        draw.text(
            (price_x, price_y),
            price_text,
            font=self._font_price,
            fill=self.TEXT_ACCENT,
        )

        current_y += self._line_height(self._font_bold) + 10

        if entry.subtitle:
            draw.text(
                (left + inner_padding_x, current_y),
                entry.subtitle,
                font=self._font_subheader,
                fill=self.TEXT_SECONDARY,
            )
            current_y += self._line_height(self._font_subheader) + 6

        if entry.meta:
            draw.text(
                (left + inner_padding_x, current_y),
                entry.meta,
                font=self._font_body,
                fill=self.TEXT_SECONDARY,
            )

    def _wrap_text(self, text: str, *, font: FontType, max_width: int) -> list[str]:
        words = text.split()
        if not words:
            return []

        lines: list[str] = []
        current_line = words[0]

        for word in words[1:]:
            candidate = f"{current_line} {word}"
            bbox = font.getbbox(candidate)
            line_width = bbox[2] - bbox[0]
            if line_width <= max_width:
                current_line = candidate
            else:
                lines.append(current_line)
                current_line = word

        lines.append(current_line)
        return lines

    def _line_height(self, font: FontType) -> int:
        bbox = font.getbbox("Ay")
        return bbox[3] - bbox[1]

    def _build_footer(self, timestamp: Optional[datetime]) -> Optional[str]:
        if timestamp is None:
            current = timezone.now()
        else:
            current = timestamp
            if timezone.is_naive(current):
                current = timezone.make_aware(current, timezone.get_default_timezone())

        formatted = current.astimezone().strftime("%Y-%m-%d %H:%M %Z")
        tz_name = getattr(settings, "TIME_ZONE", None)
        if tz_name and tz_name not in formatted:
            formatted = f"{formatted} ({tz_name})"
        return f"Published at {formatted}"

    def _derive_font(
        self,
        base_font: FontType,
        size: int,
    ) -> FontType:
        path = getattr(base_font, "path", None)
        if path:
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _load_font(
        self,
        explicit_path: Optional[Path],
        fallback_name: str,
        size: int,
    ) -> FontType:
        font_path = self._resolve_font_path(explicit_path, fallback_name)
        if font_path and font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size=size)
            except OSError:
                pass
        return ImageFont.load_default()

    def _resolve_font_path(
        self,
        explicit_path: Optional[Path],
        fallback_name: str,
    ) -> Optional[Path]:
        if explicit_path:
            return Path(explicit_path)

        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        font_root = Path(self.FONT_DIR)

        if font_root.is_absolute():
            candidate = font_root / fallback_name
        else:
            candidate = base_dir / font_root / fallback_name
        if candidate.exists():
            return candidate
        return None


