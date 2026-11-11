from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, UserActivityLog
from .permissions import is_team_manager, team_owner
from .plans import COLLABORATION_CHOICES, PLAN_GOLD, PLAN_CHOICES, normalize_plan
from .tokens import issue_tokens_for_user
from .trial import trial_expires_at


class LoginSerializer(serializers.Serializer):
    """Sign in with an email address or a username.

    Customers only ever know their email — the username is generated for them
    at signup — while staff and delegated operators still have real usernames,
    so both resolve to the same ``authenticate`` call. ``email`` is unique on
    the model, which is what makes the lookup unambiguous.
    """

    identifier = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = (attrs.get("identifier") or attrs.get("username") or "").strip()
        if not identifier:
            raise serializers.ValidationError(
                {"identifier": "Enter your email address or username."}
            )
        password = attrs.get("password") or ""
        attrs["identifier"] = identifier

        username = identifier
        if "@" in identifier:
            username = (
                CustomUser.objects.filter(email__iexact=identifier)
                .values_list("username", flat=True)
                .first()
                or identifier
            )

        user = authenticate(
            self.context.get("request"),
            username=username,
            password=password,
        )
        if not user or not user.is_active:
            raise serializers.ValidationError("Invalid credentials.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    telegram_bot_token_masked = serializers.SerializerMethodField()
    trial_days_remaining = serializers.SerializerMethodField()
    trial_expired = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "exchange_name",
            "country",
            "email",
            "phone",
            "telegram_id",
            "telegram_username",
            "website",
            "collaboration_type",
            "registered_by",
            "registered_by_name",
            "owner",
            "owner_name",
            "owner_username",
            "sub_role",
            "plan",
            "role",
            "trial_started_at",
            "trial_expires_at",
            "trial_expiry_notified_at",
            "trial_days_remaining",
            "email_verified_at",
            "onboarding_completed_at",
            "trial_expired",
            "is_active",
            "date_joined",
            "telegram_bot_token_masked",
        ]
        read_only_fields = fields

    registered_by_name = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    owner_username = serializers.SerializerMethodField()

    def get_registered_by_name(self, obj):
        staff = obj.registered_by
        if staff is None:
            return ""
        return staff.get_full_name() or staff.username

    def get_owner_name(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        return owner.get_full_name() or owner.username

    def get_owner_username(self, obj):
        owner = obj.owner
        if owner is None:
            return ""
        return owner.username

    def get_trial_expired(self, obj):
        """Explicit, because zero days remaining also means "the last day"."""
        from .trial import trial_is_expired

        return trial_is_expired(obj)

    def get_trial_days_remaining(self, obj):
        from django.utils import timezone

        if obj.trial_expires_at is None:
            return None
        return max(0, (obj.trial_expires_at - timezone.now()).days)


    def get_telegram_bot_token_masked(self, obj):
        bot = obj.telegram_bots.order_by("-created_at").first()
        if bot is None:
            return ""
        token = bot.get_plain_token()
        if not token:
            return ""
        if len(token) <= 8:
            return "••••"
        return f"{token[:4]}…{token[-4:]}"


DELEGATED_SUB_ROLES = (CustomUser.SUB_ROLE_OPERATOR, CustomUser.SUB_ROLE_HEAD_OPERATOR)


class TeamMemberFieldsMixin(serializers.Serializer):
    """Position and Telegram identity for Admin Management writes.

    A management user only ever manages its own delegated operators, so role
    and owner are fixed server-side whatever the payload says. Telegram id and
    username are unique because the bot resolves staff by them: a duplicate
    would let one desk shadow another desk's operator.
    """

    owner_username = serializers.CharField(max_length=150, required=False, allow_blank=True, write_only=True)

    def _others(self):
        qs = CustomUser.objects.all()
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        return qs

    def validate_telegram_id(self, value):
        tid = (value or "").strip()
        if tid and not tid.isdigit():
            raise serializers.ValidationError("Telegram ID must contain digits only.")
        if tid and self._others().filter(telegram_id=tid).exists():
            raise serializers.ValidationError("Another user already has this Telegram ID.")
        return tid

    def validate_telegram_username(self, value):
        uname = (value or "").strip().lstrip("@")
        if uname and self._others().filter(telegram_username__iexact=uname).exists():
            raise serializers.ValidationError("Another user already has this Telegram username.")
        return uname

    def validate(self, attrs):
        actor = self.context["request"].user
        owner_username = (attrs.pop("owner_username", "") or "").strip()
        instance = self.instance

        if is_team_manager(actor):
            attrs.pop("role", None)
            if instance is None:
                attrs["role"] = CustomUser.ROLE_EMPLOYEE
                attrs["owner"] = team_owner(actor)
                attrs.setdefault("sub_role", CustomUser.SUB_ROLE_OPERATOR)
            sub_role = attrs.get("sub_role", getattr(instance, "sub_role", None))
            if sub_role not in DELEGATED_SUB_ROLES:
                raise serializers.ValidationError({"sub_role": "Choose Operator or Head Operator."})
            return attrs

        if owner_username:
            owner = CustomUser.objects.filter(username__iexact=owner_username).first()
            if owner is None:
                raise serializers.ValidationError({"owner_username": "No user with this username exists."})
            attrs["owner"] = owner
        sub_role = attrs.get("sub_role", getattr(instance, "sub_role", CustomUser.SUB_ROLE_ADMIN))
        if sub_role in DELEGATED_SUB_ROLES:
            role = attrs.get("role", getattr(instance, "role", CustomUser.ROLE_EMPLOYEE))
            if role != CustomUser.ROLE_EMPLOYEE:
                raise serializers.ValidationError({"role": "Operators must have the employee role."})
            if attrs.get("owner", getattr(instance, "owner", None)) is None:
                raise serializers.ValidationError(
                    {"owner_username": "Owner username is required for operators."}
                )
        return attrs


class UserCreateSerializer(TeamMemberFieldsMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "password",
            "full_name",
            "role",
            "is_active",
            "sub_role",
            "telegram_id",
            "telegram_username",
            "owner_username",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        username = validated_data.pop("username")
        user = CustomUser.objects.create_user(username, password=password, **validated_data)
        return user


class UserUpdateSerializer(TeamMemberFieldsMixin, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)

    class Meta:
        model = CustomUser
        fields = [
            "full_name",
            "role",
            "is_active",
            "password",
            "sub_role",
            "telegram_id",
            "telegram_username",
            "owner_username",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        new_role = attrs.get("role")
        if instance is None or not new_role or not _is_admin(instance):
            return attrs
        if new_role == CustomUser.ROLE_SUPER_ADMIN:
            return attrs
        # Only an admin gets here, so refusing self-demotion is also what keeps
        # at least one admin on the install.
        if instance.pk == self.context["request"].user.pk:
            raise serializers.ValidationError({"role": "You cannot remove your own admin access."})
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        demoted = (
            "role" in validated_data
            and validated_data["role"] != CustomUser.ROLE_SUPER_ADMIN
            and _is_admin(instance)
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if demoted:
            # is_superuser grants everything whatever the role says, so a
            # demotion that left it set would change nothing.
            instance.is_superuser = False
            instance.is_staff = False
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


def _is_admin(user):
    return user.role == CustomUser.ROLE_SUPER_ADMIN or user.is_superuser


class MeUpdateSerializer(serializers.ModelSerializer):
    """The fields a signed-in user may change about themselves.

    Deliberately narrow: role, plan, account, trial dates and ``is_active``
    decide what the panel lets this user do, so none of them is self-service.
    """

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "full_name",
            "exchange_name",
            "country",
            "email",
            "phone",
            "telegram_username",
            "website",
        ]

    def validate_email(self, value):
        # The column is unique and nullable; "" would collide on the second
        # user who clears it, so an empty address is stored as NULL.
        cleaned = (value or "").strip().lower()
        if not cleaned:
            return None
        taken = CustomUser.objects.filter(email__iexact=cleaned)
        if self.instance is not None:
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError("This email address is already in use.")
        return cleaned

    def update(self, instance, validated_data):
        email_changed = (
            "email" in validated_data and validated_data["email"] != instance.email
        )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # A new address has not been proven yet, so the verification banner
        # comes back rather than the old proof carrying over to it.
        if email_changed:
            instance.email_verified_at = None
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Self-service password change: the current password is the authorisation."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context["request"].user)
        return value

    def validate(self, attrs):
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "The new password must differ from the current one."}
            )
        return attrs


def unique_username_from_email(email):
    local = (email or "").split("@")[0].strip().lower()
    cleaned = "".join(ch for ch in local if ch.isalnum() or ch in "._-")[:140]
    base = cleaned or "user"
    candidate = base
    n = 1
    while CustomUser.objects.filter(username__iexact=candidate).exists():
        candidate = f"{base}{n}"
        n += 1
    return candidate


class SignupSerializer(serializers.Serializer):
    """Self-serve registration: an email address in, a working panel out.

    Creates the same shape of account the programmer hub creates for a client
    (role=management, its own workspace, trial clock running) minus the
    BotFather token, which the customer adds from the panel once they are in.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, max_length=128)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    exchange_name = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    country = serializers.CharField(max_length=120, allow_blank=True, required=False, default="")
    phone = serializers.CharField(max_length=40, allow_blank=True, required=False, default="")

    def validate_email(self, value):
        email = value.strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            # Deliberately explicit: this is a signup form, not a login form, so
            # saying the address is taken helps the owner far more than it helps
            # an enumerator who could learn the same from the login page.
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        started_at = timezone.now()
        email = validated_data["email"]
        user = CustomUser.objects.create_user(
            unique_username_from_email(email),
            password=validated_data["password"],
            email=email,
            first_name=validated_data["first_name"].strip(),
            last_name=(validated_data.get("last_name") or "").strip(),
            exchange_name=(validated_data.get("exchange_name") or "").strip(),
            country=(validated_data.get("country") or "").strip(),
            phone=(validated_data.get("phone") or "").strip(),
            plan=PLAN_GOLD,
            role=CustomUser.ROLE_MANAGEMENT,
            sub_role=CustomUser.SUB_ROLE_ADMIN,
            is_active=True,
            trial_started_at=started_at,
            trial_expires_at=trial_expires_at(started_at),
        )
        return user


class GoogleSignupSerializer(serializers.Serializer):
    """Opens a desk from a verified Google profile.

    Shares :class:`SignupSerializer`'s shape — role, plan and trial clock — but
    takes its fields from Google's claims and sets no usable password: the only
    way into a Google-created account is the Google button, until the customer
    sets a password themselves.
    """

    def create_from_claims(self, claims):
        started_at = timezone.now()
        email = claims["email"].strip().lower()
        user = CustomUser.objects.create_user(
            unique_username_from_email(email),
            password=None,
            email=email,
            first_name=(claims.get("given_name") or "").strip()[:150],
            last_name=(claims.get("family_name") or "").strip()[:150],
            plan=PLAN_GOLD,
            role=CustomUser.ROLE_MANAGEMENT,
            sub_role=CustomUser.SUB_ROLE_ADMIN,
            is_active=True,
            google_sub=claims["sub"],
            email_verified_at=started_at,
            trial_started_at=started_at,
            trial_expires_at=trial_expires_at(started_at),
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        return user


class ProgrammerRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    exchange_name = serializers.CharField(max_length=255)
    country = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=40)
    telegram_id = serializers.CharField(max_length=64, allow_blank=True, required=False, default="")
    # A BotFather token is required for client accounts (they own a customer bot).
    # Delegated operators (sub_role operator/head_operator) do not own a bot, so
    # the token is optional for them — enforced in validate().
    telegram_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True, default="")
    website = serializers.URLField(max_length=256, allow_blank=True, required=False, default="")
    collaboration_type = serializers.ChoiceField(choices=COLLABORATION_CHOICES, required=False, allow_blank=True, default="")
    plan = serializers.ChoiceField(choices=PLAN_CHOICES, default=PLAN_GOLD, required=False)
    sub_role = serializers.ChoiceField(choices=CustomUser.SUB_ROLE_CHOICES, default=CustomUser.SUB_ROLE_ADMIN, required=False)
    owner_username = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    telegram_username = serializers.CharField(max_length=128, allow_blank=True, required=False, default="")

    def validate_email(self, value):
        email = value.strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate(self, attrs):
        sub_role = attrs.get("sub_role") or CustomUser.SUB_ROLE_ADMIN
        delegated = sub_role in (CustomUser.SUB_ROLE_OPERATOR, CustomUser.SUB_ROLE_HEAD_OPERATOR)
        owner_username = (attrs.get("owner_username") or "").strip()
        token = (attrs.get("telegram_bot_token") or "").strip()
        if delegated:
            if not owner_username:
                raise serializers.ValidationError(
                    {"owner_username": "Owner username is required for delegated operators."}
                )
            attrs["telegram_bot_token"] = ""
        else:
            if not token:
                raise serializers.ValidationError(
                    {"telegram_bot_token": "Bot token is required for client accounts."}
                )
            attrs["owner_username"] = ""
        attrs["owner_username"] = owner_username
        return attrs

    def _resolve_owner(self, username):
        if not username:
            return None
        owner = CustomUser.objects.filter(username__iexact=username).first()
        if owner is None:
            raise serializers.ValidationError(
                {"owner_username": "No user with this username exists."}
            )
        return owner

    def create(self, validated_data):
        import secrets

        token = validated_data.pop("telegram_bot_token")
        email = validated_data["email"]
        password = secrets.token_urlsafe(12)
        username = unique_username_from_email(email)
        plan = normalize_plan(validated_data.get("plan"))
        sub_role = validated_data.get("sub_role") or CustomUser.SUB_ROLE_ADMIN
        delegated = sub_role in (CustomUser.SUB_ROLE_OPERATOR, CustomUser.SUB_ROLE_HEAD_OPERATOR)
        owner = self._resolve_owner((validated_data.get("owner_username") or "").strip())
        registered_by = validated_data.pop("registered_by", None) or getattr(self.context.get("request"), "user", None)
        from django.utils import timezone

        started_at = timezone.now()
        user = CustomUser.objects.create_user(
            username,
            password=password,
            first_name=validated_data["first_name"].strip(),
            last_name=validated_data["last_name"].strip(),
            exchange_name=validated_data["exchange_name"].strip(),
            country=validated_data["country"].strip(),
            email=email,
            phone=validated_data["phone"].strip(),
            telegram_id=(validated_data.get("telegram_id") or "").strip(),
            telegram_username=(validated_data.get("telegram_username") or "").strip(),
            website=(validated_data.get("website") or "").strip(),
            collaboration_type=(validated_data.get("collaboration_type") or "").strip(),
            plan=plan,
            sub_role=sub_role,
            owner=owner,
            role=CustomUser.ROLE_EMPLOYEE if delegated else CustomUser.ROLE_MANAGEMENT,
            is_active=True,
            trial_started_at=started_at,
            trial_expires_at=trial_expires_at(started_at),
        )
        user.registered_by = registered_by
        user.save(update_fields=["registered_by"])
        if not delegated:
            from telegram_app.models import TelegramBot

            TelegramBot.objects.create(
                name=user.exchange_name or username,
                token=token.strip(),
                display_name=user.exchange_name or username,
                owner=user,
                is_active=True,
            )
        user._generated_password = password
        return user


class ProgrammerUserUpdateSerializer(serializers.ModelSerializer):
    telegram_bot_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    collaboration_type = serializers.ChoiceField(choices=COLLABORATION_CHOICES, required=False, allow_blank=True)
    sub_role = serializers.ChoiceField(choices=CustomUser.SUB_ROLE_CHOICES, required=False)
    # Owner is referenced by username (friendlier for admins); empty string clears it.
    owner_username = serializers.CharField(max_length=150, allow_blank=True, required=False, default="")
    telegram_username = serializers.CharField(max_length=128, allow_blank=True, required=False, default="")

    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "last_name",
            "exchange_name",
            "country",
            "email",
            "phone",
            "telegram_id",
            "telegram_username",
            "website",
            "collaboration_type",
            "sub_role",
            "owner_username",
            "plan",
            "is_active",
            "telegram_bot_token",
        ]

    def validate_owner_username(self, value):
        username = (value or "").strip()
        if not username:
            return ""
        owner = CustomUser.objects.filter(username__iexact=username).first()
        if owner is None:
            raise serializers.ValidationError("No user with this username exists.")
        if self.instance is not None and owner.id == self.instance.id:
            raise serializers.ValidationError("A user cannot be their own owner.")
        return username

    def update(self, instance, validated_data):
        token = validated_data.pop("telegram_bot_token", None)
        if "owner_username" in validated_data:
            username = validated_data.pop("owner_username")
            owner = None
            if username:
                owner = CustomUser.objects.filter(username__iexact=username).first()
                if owner is None:
                    raise serializers.ValidationError(
                        {"owner_username": "No user with this username exists."}
                    )
            validated_data["owner"] = owner
        if validated_data.get("email"):
            validated_data["email"] = validated_data["email"].strip().lower()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if token:
            from telegram_app.models import TelegramBot

            bot = instance.telegram_bots.order_by("-created_at").first()
            if bot:
                bot.token = token.strip()
                bot.save(update_fields=["token", "updated_at"])
            else:
                TelegramBot.objects.create(
                    name=instance.exchange_name or instance.username,
                    token=token.strip(),
                    owner=instance,
                    is_active=True,
                )
        return instance


class UserActivityLogSerializer(serializers.ModelSerializer):
    user_display = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()

    class Meta:
        model = UserActivityLog
        fields = [
            "id", "user", "user_display", "email", "account", "action_type",
            "ip_address", "user_agent", "details", "created_at",
        ]

    def get_user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return None

    def get_email(self, obj):
        return getattr(obj.user, "email", "") or ""

    def get_account(self, obj):
        account = getattr(obj.user, "account", None)
        return account.name if account else ""


class TokenRefreshWithVersionSerializer(TokenRefreshSerializer):
    """Add token_version to the new access token when refreshing."""

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            refresh = RefreshToken(attrs["refresh"])
            user_id = refresh.get("user_id")
            if not user_id:
                return data
            user = CustomUser.objects.filter(pk=user_id).first()
            if not user:
                return data
            impersonator = None
            impersonator_id = refresh.get("impersonator_id")
            if impersonator_id:
                impersonator = CustomUser.objects.filter(pk=impersonator_id).first()
            issued = issue_tokens_for_user(
                user, impersonator=impersonator, remember=bool(refresh.get("remember"))
            )
            data["access"] = str(issued.access_token)
            data["refresh"] = str(issued)
        except Exception:
            pass
        return data
