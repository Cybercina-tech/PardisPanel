"""
Utility functions for logging application events.
"""
from .models import Log


def log_event(level='INFO', source='system', message='', details=None, user=None):
    """
    Create a log entry in the database.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        source: Source of the log (telegram, finalize, price_publisher, etc.)
        message: Main log message
        details: Additional details (optional)
        user: User who triggered the event (optional)
    
    Returns:
        Log instance
    """
    return Log.objects.create(
        level=level,
        source=source,
        message=message,
        details=details,
        user=user
    )


def log_telegram_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Telegram events."""
    return log_event(level=level, source='telegram', message=message, details=details, user=user)


def log_finalize_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Finalize events."""
    return log_event(level=level, source='finalize', message=message, details=details, user=user)


def log_price_publisher_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Price Publisher events."""
    return log_event(level=level, source='price_publisher', message=message, details=details, user=user)


def log_template_editor_event(level='INFO', message='', details=None, user=None):
    """Convenience function to log Template Editor events."""
    return log_event(level=level, source='template_editor', message=message, details=details, user=user)

