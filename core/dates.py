"""
Shared date/time helpers for Persian (Jalali) and English date formatting.
"""
from __future__ import annotations

import jdatetime
from django.utils import timezone

from core.formatting import FARSI_MONTHS, FARSI_WEEKDAYS, to_farsi_digits


def format_persian_date(timestamp) -> str:
    """Return a Persian date string like '۵ اسفند ۱۴۰۴'."""
    now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    jalali = jdatetime.datetime.fromgregorian(datetime=now)
    raw = f"{jalali.day} {FARSI_MONTHS[jalali.month]} {jalali.year}"
    return to_farsi_digits(raw)


def format_english_date(timestamp) -> str:
    """Return an English date string like 'February 25, 2026'."""
    now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    return now.strftime("%B %d, %Y")


def get_farsi_weekday(timestamp) -> str:
    """Return the Persian weekday name for the given timestamp."""
    now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    return FARSI_WEEKDAYS.get(now.strftime("%A"), "")


def get_english_weekday(timestamp) -> str:
    now = timezone.localtime(timestamp) if timestamp else timezone.localtime()
    return now.strftime("%A")
