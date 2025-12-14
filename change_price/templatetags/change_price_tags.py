from django import template
from django.utils import timezone
from datetime import datetime
import pytz
import re

register = template.Library()


@register.filter
def sort_gbp_price_types(price_types):
    """
    Sort price types for GBP/Pound category in specific order:
    1. خرید نقدی (Buy Cash)
    2. خرید حسابی (Buy Account)
    3. فروش نقد (Sell Cash)
    4. فروش حسابی (Sell Account)
    5. فروش رسمی (Sell Official)
    
    Usage: {{ category.price_types.all|sort_gbp_price_types }}
    """
    if not price_types:
        return price_types
    
    # Convert to list if it's a queryset
    price_types_list = list(price_types)
    
    # Define order based on trade_type and name patterns
    def get_sort_key(price_type):
        name_lower = price_type.name.lower()
        trade_type = price_type.trade_type.lower()
        
        # Buy types
        if trade_type == 'buy':
            if 'نقدی' in price_type.name or 'cash' in name_lower or 'نقد' in price_type.name:
                return 1  # خرید نقدی
            elif 'حسابی' in price_type.name or 'account' in name_lower:
                return 2  # خرید حسابی
            else:
                return 10  # Other buy types
        # Sell types
        elif trade_type == 'sell':
            if 'نقد' in price_type.name or 'cash' in name_lower:
                return 3  # فروش نقد
            elif 'حسابی' in price_type.name or 'account' in name_lower:
                return 4  # فروش حسابی
            elif 'رسمی' in price_type.name or 'official' in name_lower:
                return 5  # فروش رسمی
            else:
                return 20  # Other sell types
        else:
            return 30  # Unknown types
    
    # Sort by the key
    sorted_list = sorted(price_types_list, key=get_sort_key)
    
    return sorted_list


@register.filter
def clean_gbp_name(price_type_name, category_name=''):
    """
    Remove 'پوند' or 'pound' or 'GBP' from price type name for GBP categories.
    Example: 'خرید پوند نقدی' -> 'خرید نقدی'
    
    Usage: {{ price_type.name|clean_gbp_name:category.name }}
    """
    if not price_type_name:
        return price_type_name
    
    # Check if this is a GBP category
    category_lower = category_name.lower() if category_name else ''
    is_gbp_category = 'پوند' in category_name or 'pound' in category_lower or 'gbp' in category_lower
    
    if not is_gbp_category:
        return price_type_name
    
    # Remove pound-related words from name
    cleaned = price_type_name
    # Remove 'پوند' (with spaces)
    cleaned = cleaned.replace(' پوند ', ' ').replace('پوند ', '').replace(' پوند', '')
    # Remove 'pound' (case insensitive, with spaces)
    cleaned = re.sub(r'\s*pound\s*', ' ', cleaned, flags=re.IGNORECASE)
    # Remove 'GBP' (with spaces)
    cleaned = re.sub(r'\s*gbp\s*', ' ', cleaned, flags=re.IGNORECASE)
    # Clean up multiple spaces
    cleaned = ' '.join(cleaned.split())
    
    return cleaned.strip()


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
        jalali_date = jdatetime.datetime.fromgregorian(value_tehran)
        
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


