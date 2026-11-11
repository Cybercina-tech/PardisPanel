"""Pardis Telegram captions as editable templates.

Same text the Pardis panel sent, with the dates turned into variables so the
Telegram editor can show and change them. Variables are filled in at publish time.
"""

_CONTACTS_AND_OFFICE = (
    "━━━━━━━━━━━\n"
    "💬 کارشناسان ما همواره پاسخ‌گوی شما هستند.\n"
    "📞 تماس با ما:\n"
    "1️⃣ Mr.Mahdi\n"
    "📱 <a href=\"https://wa.me/447533544249\">+44 7533 544249</a>\n"
    "2️⃣ Ms.Sogand\n"
    "📱 <a href=\"https://wa.me/447399990340\">+44 7399 990340</a>\n"
    "👤 Ms.Kianian\n"
    "📱 <a href=\"https://wa.me/989121894230\">+98 912 189 4230</a>\n\n"
    "📍 آدرس دفتر:\n"
    "🏢 <a href=\"https://maps.app.goo.gl/d3sorvbK9VRFvSBaA\">Office A, 708A High Road, North Finchley, N12 9QL</a>\n\n"
    "━━━━━━━━━━━\n"
    "🕐 ساعات کاری:\n"
    "دوشنبه تا شنبه از ۹:۳۰ صبح تا ۵ عصر (به وقت لندن)\n"
    "یکشنبه‌ها تعطیل است\n"
    "━━━━━━━━━━━\n"
    "صرافی پردیس، همراهی مطمئن در تمامی امور ارزی شما\n"
    "🌍 خدمات در لندن و لیدز"
)

TETHER_CAPTION = (
    "📅 <b>تاریخ:</b>\n\n"
    "🇮🇷 {farsi_weekday} {date_fa}\n\n"
    "🇬🇧 {english_weekday}, {date_en}\n\n"
    "━━━━━━\n\n"
    "💷 خرید فروش تتر | لیر | یورو | درهم\n\n"
    + _CONTACTS_AND_OFFICE
)

GBP_CAPTION = (
    "💷 خرید و فروش پوند (GBP)\n"
    "💰 نقدی و حسابی\n\n"
    + _CONTACTS_AND_OFFICE
)


# Appended to every price publication sent to Telegram (see with_price_notice).
PRICE_NOTICE = (
    "🪪ارائه کارت شناسایی معتبر برای  واریز بانکی الزامی میباشد\n\n"
    "📊مبالغ زیر ۱۰۰۰پوند ترانسفر بانکی شامل کارمزد میباشد\n\n"
    "به سبب نوسانات قیمت ارز، برای اطلاع از قیمت های قطعی،  تماس حاصل فرمایید"
)


def with_price_notice(caption: str | None) -> str:
    """Append PRICE_NOTICE to a caption once; idempotent so retries never duplicate it."""
    text = (caption or "").strip()
    if PRICE_NOTICE in text:
        return text
    return f"{text}\n\n{PRICE_NOTICE}" if text else PRICE_NOTICE
