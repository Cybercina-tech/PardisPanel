"""
Role-Based Access Control (RBAC) for the panel.

Roles (see accounts.models.CustomUser.ROLE_*):
- SUPER_ADMIN (super_admin): Full access to all endpoints.
- MANAGEMENT (management): the owner of one desk. Telegram
  Channels, Price Hub (read/write), Finalize, Analysis, site settings, and the
  Admin section for its own desk — its operators, their activity, and its own
  panel logs. Never another desk's anything.
- EMPLOYEE (employee): Read-only access to Price Hub and Dashboard (Finalize dashboard,
  Analysis). No access to Telegram Setup or Finalizing prices.

Permission mapping:
- User Management (list/create/update users, force logout): CanManageTeam
- Activity log: CanAuditUsers — programmers read all of it, a management user
  reads its own team's (the view narrows the queryset; the model has no account)
- Site Settings (site settings, logs): IsSuperAdminOrManagement
- Global bot/channel rows under /api/settings/: IsSuperAdmin
- Finalize (dashboard read): IsAuthenticated; (category/special/all finalize): IsSuperAdminOrManagement
- Price Hub (list/detail/history): IsAuthenticated; (update/bulk-update): IsSuperAdminOrManagement
- Telegram app (channels, send message, bots, auto-post): IsSuperAdminOrManagementOrEmployee
  (allows super_admin, management, and employee to CRUD bots and channels)
- Analysis dashboard: IsAuthenticated

Frontend permission config: frontend/src/config/permissions.js
"""
import logging

from rest_framework import permissions

from .trial import trial_is_expired

logger = logging.getLogger(__name__)

def _normalize_role(role):
    """Normalize legacy role variants (e.g. superadmin) to canonical names."""
    key = str(role or "").strip().lower().replace("-", "_")
    if key == "superadmin":
        return "super_admin"
    return key


class IsProgrammer(permissions.BasePermission):
    """developer or super_admin — programmer hub APIs only."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        role = _normalize_role(getattr(request.user, "role", None))
        return role in ("developer", "super_admin")


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to users with role super_admin.
    Used for User Management API and Site Settings.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.debug(
                "IsSuperAdmin: denied (user=%s, authenticated=%s)",
                getattr(request.user, "username", None) if request.user else None,
                getattr(request.user, "is_authenticated", False) if request.user else False,
            )
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        role = _normalize_role(getattr(request.user, "role", None))
        allowed = role == "super_admin"
        logger.debug(
            "IsSuperAdmin: user=%s role=%r allowed=%s",
            request.user.username,
            role,
            allowed,
        )
        return allowed


class IsSuperAdminOrManagement(permissions.BasePermission):
    """
    Allows access only to users with role super_admin or management.
    Used for: Telegram setup/channels, Finalize actions,
    Price Hub write (update/bulk-update), Template editor.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.debug(
                "IsSuperAdminOrManagement: denied (user=%s, authenticated=%s)",
                getattr(request.user, "username", None) if request.user else None,
                getattr(request.user, "is_authenticated", False) if request.user else False,
            )
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        role = _normalize_role(getattr(request.user, "role", None))
        allowed = role in ("super_admin", "management")
        logger.debug(
            "IsSuperAdminOrManagement: user=%s role=%r allowed=%s",
            request.user.username,
            role,
            allowed,
        )
        return allowed


def is_team_manager(user) -> bool:
    """A management user: it manages the operators it owns, never other users."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return False
    return _normalize_role(getattr(user, "role", None)) == "management"


class CanManageTeam(permissions.BasePermission):
    """Super admins manage every user; management users manage their own operators.

    This only admits the caller. Views must also narrow their queryset for
    ``is_team_manager`` users, because users are not account-scoped rows.
    """

    def has_permission(self, request, view):
        return IsSuperAdmin().has_permission(request, view) or is_team_manager(request.user)


class CanAuditUsers(permissions.BasePermission):
    """Programmers read the whole audit trail; a management user reads its team's.

    Like :class:`CanManageTeam`, this only admits the caller. ``UserActivityLog``
    carries no account column, so the view MUST narrow its queryset for a
    ``is_team_manager`` caller or one desk would read another's login IPs.
    """

    def has_permission(self, request, view):
        return IsProgrammer().has_permission(request, view) or is_team_manager(request.user)


class IsSuperAdminOrManagementOrEmployee(permissions.BasePermission):
    """
    Allows access for users with role super_admin, management, or employee.
    Used for: Telegram bots and channels CRUD (and related telegram hub actions)
    so that employees can manage bots/channels and send messages.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            logger.debug(
                "IsSuperAdminOrManagementOrEmployee: denied (user=%s, authenticated=%s)",
                getattr(request.user, "username", None) if request.user else None,
                getattr(request.user, "is_authenticated", False) if request.user else False,
            )
            return False
        if getattr(request.user, "is_superuser", False):
            return True
        role = _normalize_role(getattr(request.user, "role", None))
        allowed = role in ("super_admin", "management", "employee")
        logger.debug(
            "IsSuperAdminOrManagementOrEmployee: user=%s role=%r allowed=%s",
            request.user.username,
            role,
            allowed,
        )
        return allowed

    def has_object_permission(self, request, view, obj):
        """Allow same as request-level: super_admin, management, employee can act on any object."""
        return self.has_permission(request, view)
