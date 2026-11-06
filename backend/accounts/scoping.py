"""Per-account data isolation.

One deployment serves many self-serve customers, so every row of customer data
belongs to exactly one :class:`accounts.models.Account`. Rather than filter at
each of the ~700 call sites, the models that own data ("roots") get an
``account`` FK and this module's manager, which narrows every default queryset
to the account of the request in flight. Child rows are reached through their
parent's FK and need neither a column nor a manager.

The current account lives in a :class:`~contextvars.ContextVar` so it survives
``async``/threadpool hops and cannot leak between concurrently handled
requests the way a module global would.

Scoping **fails closed**: with no account set, a scoped manager yields nothing.
Silently returning every row would turn one forgotten ``set_current_account``
into a cross-customer data leak, whereas failing closed surfaces as an obvious
empty list. Code that legitimately spans accounts — Celery tasks, webhooks,
management commands, the owner console — says so out loud with :func:`unscoped`
or :func:`act_as_account`, both of which grep cleanly.
"""
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models

# Holds the account id (never the instance, which would pin a stale row in
# memory for the life of the request). ``UNSCOPED`` is distinct from ``None``:
# ``None`` means "nobody set this", ``UNSCOPED`` means "deliberately global".
UNSCOPED = "__unscoped__"

_current_account_id = ContextVar("current_account_id", default=None)


# Process-wide fallback used when nothing has pinned a scope. Stays ``None`` in
# production, which is what makes scoping fail closed; the test runner points it
# at the shared test account so fixtures built outside any request still land
# somewhere, including on worker threads that start with a fresh context.
_default_account_id = None


def set_default_account_id(account_id):
    global _default_account_id
    _default_account_id = account_id


def get_current_account_id():
    """The account id in force, ``UNSCOPED``, or ``None`` when unset."""
    account_id = _current_account_id.get()
    if account_id is None:
        return _default_account_id
    return account_id


def set_current_account_id(account_id):
    """Pin the account for this context. Returns a token for ``reset``."""
    return _current_account_id.set(account_id)


def reset_current_account(token):
    _current_account_id.reset(token)


@contextmanager
def unscoped():
    """Run a block against every account's data.

    For code that has no single account by nature: Celery beat sweeps, inbound
    webhooks, management commands, and the owner console. Deliberately verbose
    to read and trivial to grep for during an audit.
    """
    token = _current_account_id.set(UNSCOPED)
    try:
        yield
    finally:
        _current_account_id.reset(token)


@contextmanager
def act_as_account(account):
    """Run a block as one specific account.

    The counterpart to :func:`unscoped` for background work that *does* belong
    to a customer — a publish task, a scheduled auto-post — so the task body
    reads exactly like request-time code.
    """
    account_id = getattr(account, "pk", account)
    token = _current_account_id.set(account_id)
    try:
        yield
    finally:
        _current_account_id.reset(token)


class AccountScopedQuerySet(models.QuerySet):
    """Queryset that knows how to drop back to every account's rows."""

    def unscoped(self):
        """This queryset without the account filter, regardless of context."""
        return self.model._base_manager.get_queryset()


class AccountScopedManager(models.Manager.from_queryset(AccountScopedQuerySet)):
    """Default manager for root models; narrows to the current account.

    Django uses ``_base_manager`` for related-object descriptors and
    ``_default_manager`` for most everything else, so assigning this as
    ``objects`` scopes ordinary queries while leaving FK traversal from an
    already-scoped parent intact.
    """

    def get_queryset(self):
        queryset = super().get_queryset()
        account_id = get_current_account_id()
        if account_id is UNSCOPED or account_id == UNSCOPED:
            return queryset
        if account_id is None:
            return queryset.none()
        return queryset.filter(account_id=account_id)


class RelatedScopedManagerBase(models.Manager.from_queryset(AccountScopedQuerySet)):
    """Scopes a child model through the FK path that reaches an account."""

    account_path = None

    def get_queryset(self):
        queryset = super().get_queryset()
        account_id = get_current_account_id()
        if account_id is UNSCOPED or account_id == UNSCOPED:
            return queryset
        if account_id is None:
            return queryset.none()
        return queryset.filter(**{self.account_path: account_id})


def RelatedScopedManager(account_path):
    """Default manager for a child model, scoping through its parent's account.

    Most child rows are only ever reached from an already-scoped parent and need
    nothing. This is for the ones code queries head-on — price types, price
    history, exchange requests — where starting at the child would otherwise
    walk straight past the account filter. ``account_path`` is the ORM lookup
    from this model to the owning account id, e.g.
    ``"price_type__category__account_id"``.

    The path is a class attribute rather than a constructor argument because
    Django builds related managers by re-instantiating the default manager's
    class with no arguments.
    """
    return type(
        "RelatedScopedManager", (RelatedScopedManagerBase,), {"account_path": account_path}
    )()


class AccountScopedModel(models.Model):
    """Mixin for the root models that own customer data."""

    # Not editable: the owning account is never client input. ``save()`` stamps
    # it from the context, and ``editable=False`` keeps it out of ModelForms and
    # ``ModelSerializer`` field sets so no request can ever name its own account.
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_set",
        editable=False,
        db_index=True,
    )

    objects = AccountScopedManager()
    # Kept unscoped on purpose: migrations, ``dumpdata`` and the admin need a
    # manager that never hides rows, and Django resolves related descriptors
    # through it.
    all_objects = models.Manager()

    class Meta:
        abstract = True
        # Related-object descriptors (``some_root.<related>``) resolve through
        # the base manager. Pointing it at the unscoped manager means traversing
        # from an already-owned parent — e.g. ``user.telegram_bots`` — sees that
        # parent's children regardless of the contextvar. The scoped default
        # manager still governs every top-level query.
        base_manager_name = "all_objects"

    def save(self, *args, **kwargs):
        """Stamp the owning account on creation when the context knows it."""
        if self.account_id is None:
            account_id = get_current_account_id()
            if account_id is None or account_id == UNSCOPED:
                account_id = self._scope_account_id()
            if account_id is not None and account_id != UNSCOPED:
                self.account_id = account_id
        super().save(*args, **kwargs)

    def _scope_account_id(self):
        """An account to default to when none is in context.

        Models with a natural owner (e.g. a ``TelegramBot`` owned by a desk)
        override this to stamp their parent's account so request-less creation
        still lands on the right desk. Returns ``None`` by default.
        """
        return None


def resolve_public_account_id(slug=None):
    """The account a public, unauthenticated request should read.

    Public endpoints (a price feed, an order form) have no user to scope from,
    so the caller names the desk with ``?account=<slug>``. A single-account
    deployment — an on-prem install, or dev — is unambiguous and needs no slug,
    which keeps those URLs working unchanged. Anything else returns ``None``,
    and ``None`` scopes to nothing rather than to everything.
    """
    from .models import Account

    slug = (slug or "").strip()
    if slug:
        return Account.objects.filter(slug=slug).values_list("pk", flat=True).first()
    ids = list(Account.objects.values_list("pk", flat=True)[:2])
    return ids[0] if len(ids) == 1 else None


def public_account_slug(user):
    """The ``?account=`` slug a public link for ``user``'s desk must carry.

    Public endpoints have no user to scope from, so an unauthenticated form can
    only reach the right desk if its URL names it. Staff belong to no account
    and get ``None``.
    """
    from .models import Account

    account_id = account_for_user(user)
    if account_id is None:
        return None
    with unscoped():
        return Account.objects.filter(pk=account_id).values_list("slug", flat=True).first()


def account_for_user(user):
    """The account a user's data belongs to, or ``None`` for staff.

    Delegated operators (``CustomUser.owner``) share their owner's account, so
    a sub-operator sees exactly the desk they were hired onto.

    Takes any authenticated principal, not just a ``CustomUser``: a bot customer
    holding a gateway JWT carries an account the same way and must scope to it.
    """
    if user is None:
        return None
    account_id = getattr(user, "account_id", None)
    if account_id is not None:
        return account_id
    owner = getattr(user, "owner", None)
    if owner is not None:
        return getattr(owner, "account_id", None)
    return None
