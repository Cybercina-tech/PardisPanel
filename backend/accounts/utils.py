"""
Utilities for auth: client IP, user agent, activity logging.
"""

def get_client_ip(request):
    """Extract client IP from request, considering X-Forwarded-For."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()[:45]  # first proxy client
    return request.META.get('REMOTE_ADDR', '')[:45]


def get_user_agent(request):
    """Extract User-Agent from request."""
    return (request.META.get('HTTP_USER_AGENT') or '')[:500]


def log_activity(user, action_type, request, details=''):
    """Create a UserActivityLog entry. Safe to call with request from APIView."""
    from .models import UserActivityLog
    return UserActivityLog.objects.create(
        user=user,
        action_type=action_type,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        details=details[:2000] if details else '',
    )
