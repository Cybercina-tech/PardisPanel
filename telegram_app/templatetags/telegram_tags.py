"""
Custom template tags for telegram_app.
"""
from django import template

register = template.Library()


@register.filter
def add_class(field, css_class):
    """
    Add a CSS class to a form field.
    
    Usage:
        {{ form.field|add_class:"form-control" }}
    """
    if field and field.field:
        attrs = field.field.widget.attrs
        if 'class' in attrs:
            attrs['class'] = f"{attrs['class']} {css_class}"
        else:
            attrs['class'] = css_class
    return field
