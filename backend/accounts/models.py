from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from .managers import CustomUserManager
from .plans import PLAN_GOLD, PLAN_CHOICES


class Account(models.Model):
    """One customer desk: the isolation boundary for all customer data.

    Created for every self-serve signup and owned by the user who signed up.
    Staff and ``super_admin`` belong to no account, which is how they see
    across all of them. See ``accounts.scoping`` for how rows are narrowed.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    # Set when a sale converts the account; a paid account is never walled by
    # TrialAccessMiddleware even after its trial dates lapse.
    is_paid = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_MANAGEMENT = 'management'
    ROLE_EMPLOYEE = 'employee'
    ROLE_DEVELOPER = 'developer'

    ROLE_CHOICES = (
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_MANAGEMENT, 'Management'),
        (ROLE_EMPLOYEE, 'Employee'),
        (ROLE_DEVELOPER, 'Developer'),
    )

    # Sub-roles refine what a Telegram bot admin (including delegated employees)
    # may do inside the in-bot admin panel. Full admins keep SUB_ROLE_ADMIN.
    SUB_ROLE_ADMIN = 'admin'
    SUB_ROLE_OPERATOR = 'operator'
    SUB_ROLE_HEAD_OPERATOR = 'head_operator'

    SUB_ROLE_CHOICES = (
        (SUB_ROLE_ADMIN, 'Admin'),
        (SUB_ROLE_OPERATOR, 'Operator'),
        (SUB_ROLE_HEAD_OPERATOR, 'Head Operator'),
    )

    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    full_name = models.CharField(max_length=255, blank=True)
    exchange_name = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True, null=True, unique=True)
    phone = models.CharField(max_length=40, blank=True)
    telegram_id = models.CharField(max_length=64, blank=True)
    website = models.URLField(max_length=256, blank=True, default='')
    collaboration_type = models.CharField(max_length=32, blank=True, default='', help_text='Partnership model / service tier')
    registered_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='registered_users',
        help_text='Admin who registered this user'
    )
    # Delegated Telegram bot admins: employee-role users granted access to the
    # in-bot admin panel of their owner's bots via telegram_app.BotAdmin rows.
    owner = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sub_users',
        help_text='Panel user this delegated operator reports to'
    )
    # The customer desk this user's data belongs to. Null for staff and
    # super_admins, who work across every account.
    account = models.ForeignKey(
        'accounts.Account', on_delete=models.CASCADE, null=True, blank=True,
        related_name='users',
        help_text='Customer account whose data this user works on'
    )
    sub_role = models.CharField(max_length=24, choices=SUB_ROLE_CHOICES, default=SUB_ROLE_ADMIN)
    telegram_username = models.CharField(max_length=128, blank=True, default='')
    plan = models.CharField(max_length=16, choices=PLAN_CHOICES, default=PLAN_GOLD)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_EMPLOYEE)
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_expires_at = models.DateTimeField(null=True, blank=True)
    trial_expiry_notified_at = models.DateTimeField(null=True, blank=True)
    # Self-serve signups reach their panel immediately; this only records that
    # the address was later proven, so the panel can nag and staff can filter.
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # Server-side rather than a browser flag: the guided tour should not reopen
    # because someone signed in from a second machine or cleared their storage.
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    # Google's stable subject id, not the email: an address can be reassigned
    # inside a Workspace domain, the sub cannot.
    google_sub = models.CharField(max_length=64, blank=True, default="", db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    token_version = models.PositiveIntegerField(default=0, help_text='Incremented on force logout to invalidate all tokens.')

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def save(self, *args, **kwargs):
        composed = f"{self.first_name} {self.last_name}".strip()
        if composed:
            self.full_name = composed
        if self.email == "":
            self.email = None
        # Every customer desk owns an Account; each row of their data lives
        # under it. Staff and owners of no desk stay account-less (UNSCOPED).
        self._ensure_account()
        super().save(*args, **kwargs)

    def _ensure_account(self):
        """Assign this user an Account unless they are staff or already have one.

        The isolation model is one desk per Account: a standalone operator
        (management) owns its own; a delegated operator (employee) inherits the
        desk it reports to via ``owner``. Staff, ``super_admin`` and
        ``developer`` see every account and belong to none. Runs on every save,
        but only ever *creates* an Account for a brand-new user, so re-saving an
        existing user is a no-op.
        """
        if self.account_id is not None:
            return
        if getattr(self, "is_staff", False) or getattr(self, "is_superuser", False):
            return
        if self.role in (CustomUser.ROLE_SUPER_ADMIN, CustomUser.ROLE_DEVELOPER):
            return
        owner = self.owner
        if owner is not None and owner.account_id is not None:
            self.account = owner.account
            return
        if not self._state.adding:
            return
        # A user created from inside a desk's own session joins that desk; only
        # a signup (unauthenticated) or a staff-initiated registration
        # (UNSCOPED) reaches the branch below that opens a new one.
        from .scoping import UNSCOPED, get_current_account_id

        scoped_account_id = get_current_account_id()
        if scoped_account_id not in (None, UNSCOPED):
            self.account_id = scoped_account_id
            return
        account = Account.objects.create(
            name=self.exchange_name or self.full_name or self.username,
            slug=self._account_slug(),
        )
        self.account = account

    def ensure_account(self):
        """Give an account-less desk user an Account now, and persist it.

        ``_ensure_account`` only ever opens a desk while the row is being
        created, so users that predate per-account isolation keep
        ``account_id`` NULL. Every scoped manager fails closed on them, which
        surfaces as an empty panel — a connected Telegram bot reported as "no
        bot connected", prices that vanish — so the request boundary heals such
        a user instead of serving them nothing.

        Returns the account id in force, or ``None`` for principals that
        legitimately belong to no desk (staff, super_admin, developer).
        """
        if self.account_id is not None:
            return self.account_id
        if getattr(self, "is_staff", False) or getattr(self, "is_superuser", False):
            return None
        if self.role in (CustomUser.ROLE_SUPER_ADMIN, CustomUser.ROLE_DEVELOPER):
            return None
        if not self.pk:
            return None

        owner = self.owner
        if owner is not None:
            owner_account_id = owner.account_id or owner.ensure_account()
            if owner_account_id is not None:
                self._attach_account(owner_account_id)
                return self.account_id

        account = Account.objects.create(
            name=self.exchange_name or self.full_name or self.username,
            slug=self._account_slug(),
        )
        self._attach_account(account.pk)
        return self.account_id

    def _attach_account(self, account_id):
        """Write the account FK without replaying the rest of ``save()``."""
        self.account_id = account_id
        CustomUser.objects.filter(pk=self.pk).update(account_id=account_id)

    def _account_slug(self):
        base = (self.username or self.email or "account")
        slug = base.lower().strip().replace(" ", "-")[:120]
        candidate, n = slug, 1
        while Account.objects.filter(slug=candidate).exists():
            candidate = f"{slug}-{n}"
            n += 1
        return candidate

    def get_full_name(self):
        composed = f"{self.first_name} {self.last_name}".strip()
        return composed or self.full_name or self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.get_full_name()


class UserActivityLog(models.Model):
    """Audit log for logins, logouts, and sensitive actions."""

    ACTION_SIGNUP = 'signup'
    ACTION_LOGIN_SUCCESS = 'login_success'
    ACTION_LOGIN_FAILED = 'login_failed'
    ACTION_LOGOUT = 'logout'
    ACTION_PRICE_UPDATE = 'price_update'
    ACTION_BULK_PRICE_UPDATE = 'bulk_price_update'
    ACTION_SPECIAL_PRICE_UPDATE = 'special_price_update'
    ACTION_TEMPLATE_CHANGE = 'template_change'
    ACTION_FINALIZE = 'finalize'
    ACTION_IMPERSONATE_START = 'impersonate_start'
    ACTION_OTHER = 'other'

    ACTION_CHOICES = (
        (ACTION_SIGNUP, 'Signup'),
        (ACTION_LOGIN_SUCCESS, 'Login success'),
        (ACTION_LOGIN_FAILED, 'Login failed'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_PRICE_UPDATE, 'Price update'),
        (ACTION_BULK_PRICE_UPDATE, 'Bulk price update'),
        (ACTION_SPECIAL_PRICE_UPDATE, 'Special price update'),
        (ACTION_TEMPLATE_CHANGE, 'Template change'),
        (ACTION_FINALIZE, 'Finalize'),
        (ACTION_IMPERSONATE_START, 'Impersonate start'),
        (ACTION_OTHER, 'Other'),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action_type = models.CharField(max_length=32, choices=ACTION_CHOICES)
    ip_address = models.CharField(max_length=45, blank=True)  # IPv6 max length
    user_agent = models.TextField(blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
        verbose_name = 'User activity log'
        verbose_name_plural = 'User activity logs'

    def __str__(self):
        return f'{self.action_type} - {self.created_at}'
