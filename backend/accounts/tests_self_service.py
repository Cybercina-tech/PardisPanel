"""Account page endpoints and the account-less-user repair they depend on."""

from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.middleware import account_scope_for_user
from accounts.models import CustomUser
from accounts.scoping import act_as_account, unscoped
from telegram_app.models import TelegramBot
from telegram_app.ownership import resolve_bot_for_user


def _orphan(username, **extra):
    """A desk user with no Account, as users created before scoping existed."""
    with unscoped():
        user = CustomUser.objects.create_user(
            username=username,
            password="pass12345",
            role=CustomUser.ROLE_MANAGEMENT,
            **extra,
        )
        CustomUser.objects.filter(pk=user.pk).update(account=None)
    user.refresh_from_db()
    return user


class AccountHealingTests(APITestCase):
    """Scoping fails closed, so an account-less desk sees none of its own data."""

    def test_orphan_user_gets_an_account_at_request_scope(self):
        user = _orphan("legacy")
        self.assertIsNone(user.account_id)

        account_id = account_scope_for_user(user)

        self.assertIsNotNone(account_id)
        user.refresh_from_db()
        self.assertEqual(user.account_id, account_id)

    def test_delegated_operator_joins_its_owners_desk(self):
        owner = _orphan("owner-desk")
        with unscoped():
            operator = CustomUser.objects.create_user(
                username="operator",
                password="pass12345",
                role=CustomUser.ROLE_EMPLOYEE,
                owner=owner,
            )
            CustomUser.objects.filter(pk=operator.pk).update(account=None)
        operator.refresh_from_db()

        account_id = account_scope_for_user(operator)

        owner.refresh_from_db()
        self.assertEqual(account_id, owner.account_id)

    def test_staff_stay_account_less(self):
        staff = CustomUser.objects.create_user(
            username="root", password="pass12345", role=CustomUser.ROLE_SUPER_ADMIN
        )
        self.assertIsNone(staff.ensure_account())

    def test_connected_bot_is_visible_once_the_desk_has_an_account(self):
        """The reported symptom: a bot exists but the hub reports `no_bot`."""
        user = _orphan("hubless")
        self.client.force_authenticate(user=user)

        # A bot connected from this desk, under the scope the repair hands out
        # (on a real request the middleware pins it before the view runs).
        account_id = account_scope_for_user(user)
        with act_as_account(account_id):
            bot = TelegramBot(name="Desk bot", token="123:ABC", owner=user)
            bot.save()
            self.assertEqual(bot.account_id, account_id)

            resolved, code, _ = resolve_bot_for_user(user)

        self.assertIsNone(code)
        self.assertEqual(resolved.pk, bot.pk)


class BotOwnershipTests(APITestCase):
    def test_creator_owns_the_bot_whatever_their_role(self):
        with unscoped():
            owner = CustomUser.objects.create_user(
                username="desk", password="pass12345", role=CustomUser.ROLE_MANAGEMENT
            )
        employee = CustomUser.objects.create_user(
            username="clerk",
            password="pass12345",
            role=CustomUser.ROLE_EMPLOYEE,
            owner=owner,
        )
        self.client.force_authenticate(user=employee)

        response = self.client.post(
            "/api/telegram/bots/",
            {
                "name": "Clerk bot",
                "token": "123456789:AAHclerkbottokenexample0123456789ab",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        bot = TelegramBot.all_objects.get(pk=response.data["id"])
        self.assertEqual(bot.owner_id, employee.pk)


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        with unscoped():
            self.user = CustomUser.objects.create_user(
                username="ada",
                password="pass12345",
                role=CustomUser.ROLE_MANAGEMENT,
                email="ada@example.com",
            )
        self.client.force_authenticate(user=self.user)

    def test_patch_me_updates_own_profile(self):
        response = self.client.patch(
            "/api/auth/me/",
            {"full_name": "Ada Lovelace", "phone": "+441234567890"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Ada Lovelace")
        self.assertEqual(self.user.phone, "+441234567890")

    def test_role_and_plan_are_not_self_service(self):
        response = self.client.patch(
            "/api/auth/me/",
            {"role": CustomUser.ROLE_SUPER_ADMIN, "plan": "gold", "is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, CustomUser.ROLE_MANAGEMENT)
        self.assertTrue(self.user.is_active)

    def test_a_new_email_has_to_be_verified_again(self):
        self.user.email_verified_at = "2024-01-01T00:00:00Z"
        self.user.save(update_fields=["email_verified_at"])

        response = self.client.patch(
            "/api/auth/me/", {"email": "ada@newdomain.test"}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ada@newdomain.test")
        self.assertIsNone(self.user.email_verified_at)

    def test_email_already_taken_is_rejected(self):
        with unscoped():
            CustomUser.objects.create_user(
                username="grace",
                password="pass12345",
                role=CustomUser.ROLE_MANAGEMENT,
                email="grace@example.com",
            )

        response = self.client.patch(
            "/api/auth/me/", {"email": "GRACE@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data["errors"])


@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "accounts.auth.JWTAuthenticationWithTokenVersion"
        ],
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
)
class ChangePasswordTests(APITestCase):
    def setUp(self):
        with unscoped():
            self.user = CustomUser.objects.create_user(
                username="ada", password="oldpass12345", role=CustomUser.ROLE_MANAGEMENT
            )
        self.client.force_authenticate(user=self.user)

    def test_password_change_rotates_tokens(self):
        before = self.user.token_version

        response = self.client.post(
            "/api/auth/me/password/",
            {"current_password": "oldpass12345", "new_password": "brandnew98765"},
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brandnew98765"))
        self.assertEqual(self.user.token_version, before + 1)

    def test_wrong_current_password_is_rejected(self):
        response = self.client.post(
            "/api/auth/me/password/",
            {"current_password": "notitatall", "new_password": "brandnew98765"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("oldpass12345"))

    def test_new_password_must_differ(self):
        response = self.client.post(
            "/api/auth/me/password/",
            {"current_password": "oldpass12345", "new_password": "oldpass12345"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_anonymous_callers_are_refused(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/auth/me/password/",
            {"current_password": "oldpass12345", "new_password": "brandnew98765"},
            format="json",
        )

        self.assertIn(response.status_code, (401, 403))
