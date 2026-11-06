"""Subscription plans that gate picture templates."""

# Partnership / collaboration models for registered clients
COLLABORATION_RESELLER = "reseller"
COLLABORATION_WHITE_LABEL = "white_label"
COLLABORATION_AGENCY = "agency"
COLLABORATION_DIRECT = "direct"

COLLABORATION_CHOICES = (
    (COLLABORATION_RESELLER, "Reseller"),
    (COLLABORATION_WHITE_LABEL, "White Label"),
    (COLLABORATION_AGENCY, "Agency"),
    (COLLABORATION_DIRECT, "Direct"),
)

# Gold is the only plan; retired tiers (bronze/silver) still stored anywhere
# resolve to Gold so every account keeps full access.
PLAN_GOLD = "gold"

PLAN_CHOICES = (
    (PLAN_GOLD, "Gold"),
)

PLAN_RANK = {
    PLAN_GOLD: 0,
}


def normalize_plan(plan):
    key = str(plan or PLAN_GOLD).strip().lower()
    if key not in PLAN_RANK:
        return PLAN_GOLD
    return key


def allowed_plans_for(plan):
    rank = PLAN_RANK[normalize_plan(plan)]
    return [name for name, value in PLAN_RANK.items() if value <= rank]


def user_plan(user):
    return normalize_plan(getattr(user, "plan", None))


# ── Customer-bot abilities gated by the bot owner's plan ─────────────────────
# A TelegramBot row owned by a panel user inherits that user's plan. Bots with
# no owner (e.g. internal/legacy bots) default to having every ability.
CUSTOMER_PROFILE_ABILITY = "customer_profile"
EXCHANGE_REQUESTS_ABILITY = "exchange_requests"
PRICE_ALERTS_ABILITY = "price_alerts"
ADMIN_MENU_ABILITY = "admin_menu"

# Minimum plan required per customer-bot ability.
ABILITY_MIN_PLAN = {
    CUSTOMER_PROFILE_ABILITY: PLAN_GOLD,
    EXCHANGE_REQUESTS_ABILITY: PLAN_GOLD,
    PRICE_ALERTS_ABILITY: PLAN_GOLD,
    ADMIN_MENU_ABILITY: PLAN_GOLD,
}


def bot_has_ability(bot, ability):
    """Whether a TelegramBot may expose a customer-bot feature.

    Gates on the bot owner's subscription plan. Bots without an owner are
    treated as fully enabled so existing/internal bots never lose features;
    unknown abilities are likewise allowed (forward-compatible).
    """
    if not ability:
        return True
    min_plan = ABILITY_MIN_PLAN.get(ability)
    if min_plan is None:
        return True
    owner = getattr(bot, "owner", None)
    if owner is None or not getattr(owner, "is_authenticated", False):
        return True
    owner_plan = normalize_plan(getattr(owner, "plan", None))
    return PLAN_RANK[owner_plan] >= PLAN_RANK[min_plan]


def is_impersonating(request):
    token = getattr(request, "auth", None)
    if token is None:
        return False
    try:
        return bool(token.get("impersonator_id"))
    except Exception:
        return False


def is_programmer_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = str(getattr(user, "role", "") or "").strip().lower().replace("-", "_")
    if role == "superadmin":
        role = "super_admin"
    return role in ("developer", "super_admin")


def can_see_all_templates(request):
    user = getattr(request, "user", None)
    return is_programmer_user(user) and not is_impersonating(request)


def can_assign_template_plan(request):
    return can_see_all_templates(request)


def filter_templates_queryset(queryset, request):
    if can_see_all_templates(request):
        return queryset
    user = getattr(request, "user", None)
    return queryset.filter(plan__in=allowed_plans_for(user_plan(user)))


def user_may_use_template(user, template, request=None):
    if request is not None and can_see_all_templates(request):
        return True
    template_plan = normalize_plan(getattr(template, "plan", None))
    return PLAN_RANK[template_plan] <= PLAN_RANK[user_plan(user)]
