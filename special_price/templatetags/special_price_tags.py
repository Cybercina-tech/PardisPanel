from django import template
from django.utils import timezone
from datetime import datetime
import pytz

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using its key.
    Usage: {{ my_dict|get_item:key_variable }}
    """
    return dictionary.get(str(key))


@register.filter
def get_form_field(form, field_name):
    """
    Get a form field by name.
    Usage: {{ form|get_form_field:"price_1" }}
    """
    try:
        if hasattr(form, field_name):
            return getattr(form, field_name)
        # Try dictionary-style access for dynamically created fields
        if hasattr(form, 'fields') and field_name in form.fields:
            # Return a BoundField for the field
            from django.forms.boundfield import BoundField
            field = form.fields[field_name]
            return BoundField(form, field, field_name)
        return None
    except (KeyError, AttributeError, TypeError):
        return None


@register.filter
def to_jalali(value, format_string="%Y/%m/%d %H:%M"):
    """
    Convert a datetime object to Jalali (Persian) date format.
    First converts to Tehran timezone, then converts to Jalali.
    Usage: {{ date|to_jalali:"%Y/%m/%d %H:%M" }}
    """
    if not value:
        return ""
    
    try:
        # Import jdatetime
        import jdatetime
        
        # Convert to Tehran timezone if timezone-aware
        if timezone.is_aware(value):
            tehran_tz = pytz.timezone('Asia/Tehran')
            value_tehran = value.astimezone(tehran_tz)
        else:
            # If naive, assume it's in UTC and convert
            utc_tz = pytz.UTC
            tehran_tz = pytz.timezone('Asia/Tehran')
            value_tehran = utc_tz.localize(value).astimezone(tehran_tz)
        
        # Convert to Jalali
        jalali_date = jdatetime.datetime.fromgregorian(datetime=value_tehran)
        
        # Format the Jalali date
        # Persian month names
        persian_months = {
            1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد', 4: 'تیر',
            5: 'مرداد', 6: 'شهریور', 7: 'مهر', 8: 'آبان',
            9: 'آذر', 10: 'دی', 11: 'بهمن', 12: 'اسفند'
        }
        
        # Format based on format_string
        if format_string == "short":
            # Short format: 1403/01/15 14:30
            return jalali_date.strftime("%Y/%m/%d %H:%M")
        elif format_string == "long":
            # Long format with Persian month name: 15 فروردین 1403، 14:30
            return f"{jalali_date.day} {persian_months[jalali_date.month]} {jalali_date.year}، {jalali_date.strftime('%H:%M')}"
        elif format_string == "date_only":
            # Date only: 1403/01/15
            return jalali_date.strftime("%Y/%m/%d")
        elif format_string == "time_only":
            # Time only: 14:30
            return jalali_date.strftime("%H:%M")
        else:
            # Default: use the format string (with Jalali replacements)
            result = format_string
            result = result.replace("%Y", str(jalali_date.year))
            result = result.replace("%m", f"{jalali_date.month:02d}")
            result = result.replace("%d", f"{jalali_date.day:02d}")
            result = result.replace("%H", f"{jalali_date.hour:02d}")
            result = result.replace("%M", f"{jalali_date.minute:02d}")
            result = result.replace("%S", f"{jalali_date.second:02d}")
            # Replace month number with Persian name if requested
            if "%B" in result:
                result = result.replace("%B", persian_months[jalali_date.month])
            return result
    except ImportError:
        # If jdatetime is not installed, return empty string
        return ""
    except Exception as e:
        # Return empty string on any error
        return ""

