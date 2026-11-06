"""
Templates for Telegram captions and inline keyboards.

NOTE: Prefer using SiteSettings-driven captions from price_publisher.services.publisher
(_build_legacy_final_message, _build_legacy_final_buttons). Configure Logo, Favicon,
Support Phone, Office URL, and Business Hours in Django Admin > Site Settings.
"""


def get_legacy_caption_from_settings():
    """Build legacy-style caption from SiteSettings. Use for custom integrations."""
    from setting.models import SiteSettings
    s = SiteSettings.load()
    lines = ["💷 خرید فروش تتر و پوند نقدی و حسابی\n🔺🔺🔺🔺🔺🔺🔺🔺🔺"]
    if s.support_phone:
        lines.append(f"تماس ۱    📞  {s.support_phone}\n")
    if s.support_phone_2:
        lines.append(f"تماس ۲    📞  {s.support_phone_2}\n")
    if s.support_phone_3:
        lines.append(f"مدیر مالی    📞  {s.support_phone_3}\n")
    lines.append("🔺🔺🔺🔺🔺🔺🔺🔺🔺")
    if s.address:
        lines.append(f"📌آدرس دفتر :\n<u>{s.address}</u>\n\n")
    lines.append("🔺🔺🔺🔺🔺🔺🔺🔺🔺\n\n")
    lines.append("مبالغ زیر ۱۰۰۰ پوند شامل ۱۰ پوند کارمزد می‌باشد\n\n")
    lines.append("⛔ لطفا بدون هماهنگی هیچ مبلغی به هیچ حسابی واریز نکنید ⛔")
    return "\n".join(lines)


def get_legacy_buttons_from_settings():
    """Build legacy inline buttons from SiteSettings."""
    from setting.models import SiteSettings
    s = SiteSettings.load()
    buttons = []
    if s.support_phone:
        c = s.support_phone.replace("+", "").replace(" ", "")
        buttons.append([{"text": "ارتباط با امور مشتریان ۱", "url": f"https://wa.me/{c}"}])
    if s.support_phone_2:
        c = s.support_phone_2.replace("+", "").replace(" ", "")
        buttons.append([{"text": "ارتباط با امور مشتریان ۲", "url": f"https://wa.me/{c}"}])
    if s.support_phone_3:
        c = s.support_phone_3.replace("+", "").replace(" ", "")
        buttons.append([{"text": "مدیر مالی", "url": f"https://wa.me/{c}"}])
    row = []
    if s.telegram_link:
        row.append({"text": "کانال تلگرام ما", "url": s.telegram_link})
    if s.instagram_link:
        row.append({"text": "اینستاگرام", "url": s.instagram_link})
    if row:
        buttons.append(row)
    return buttons


# Legacy constants - deprecated. Use get_legacy_caption_from_settings() and get_legacy_buttons_from_settings().
PARDIS_PRICE_CAPTION = None  # Use get_legacy_caption_from_settings()
PARDIS_INLINE_BUTTONS = None  # Use get_legacy_buttons_from_settings()

