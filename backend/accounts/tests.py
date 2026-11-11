from django.conf import settings
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from accounts.emails import make_verification_token
from accounts.models import CustomUser, UserActivityLog
from accounts.plans import PLAN_GOLD
from price_publisher.models import PriceTemplate
from telegram_app.models import TelegramBot


def _tiny_png():
    return SimpleUploadedFile(
        "bg.png",
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82",
        content_type="image/png",
    )


class ProgrammerHubApiTests(APITestCase):
    def setUp(self):
        self.programmer = CustomUser.objects.create_user(
            username="dev",
            password="pass12345",
            role=CustomUser.ROLE_DEVELOPER,
        )
        self.staff = CustomUser.objects.create_user(
            username="desk",
            password="pass12345",
            role=CustomUser.ROLE_MANAGEMENT,
            plan=PLAN_GOLD,
            email="desk@example.com",
        )
        self.employee = CustomUser.objects.create_user(
            username="emp",
            password="pass12345",
            role=CustomUser.ROLE_EMPLOYEE,
        )

    def test_employee_lists_users_like_management(self):
        self.client.force_authenticate(self.employee)
        r = self.client.get("/api/auth/users/")
        self.assertEqual(r.status_code, 200)

    def test_programmer_lists_users(self):
        self.client.force_authenticate(self.programmer)
        r = self.client.get("/api/auth/users/")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        items = body["results"] if isinstance(body, dict) and "results" in body else body
        self.assertGreaterEqual(len(items), 2)

    def test_register_and_upgrade_plan(self):
        self.client.force_authenticate(self.programmer)
        r = self.client.post(
            "/api/auth/programmer/users/",
            {
                "first_name": "Ada",
                "last_name": "Lovelace",
                "exchange_name": "Ada FX",
                "country": "UK",
                "email": "ada@example.com",
                "phone": "+44111",
                "telegram_id": "123",
                "telegram_bot_token": "111:bot-token-plain",
                "plan": "gold",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        data = r.json()
        self.assertEqual(data["plan"], "gold")
        self.assertEqual(data["role"], CustomUser.ROLE_MANAGEMENT)
        self.assertTrue(data.get("generated_password"))
        self.assertIn("…", data.get("telegram_bot_token_masked") or "")
        user = CustomUser.objects.get(email="ada@example.com")
        # Registration puts the new customer on their own account, so this bot
        # lives outside the account the test itself runs under.
        bot = TelegramBot.all_objects.get(owner=user)
        self.assertNotEqual(bot.token, "111:bot-token-plain")
        self.assertEqual(bot.get_plain_token(), "111:bot-token-plain")

        r2 = self.client.patch(
            f"/api/auth/programmer/users/{user.pk}/",
            {"plan": "gold"},
            format="json",
        )
        self.assertEqual(r2.status_code, 200, r2.content)
        self.assertEqual(r2.json()["plan"], "gold")

    def test_programmer_user_account_detail_tabs(self):
        self.client.force_authenticate(self.programmer)
        TelegramBot.objects.create(
            name="Desk Bot",
            token="222:desk-bot-token",
            owner=self.staff,
            is_active=True,
        )
        UserActivityLog.objects.create(
            user=self.staff,
            action_type=UserActivityLog.ACTION_LOGIN_SUCCESS,
            details="test",
        )
        PriceTemplate.objects.create(
            name="Gold board",
            template_type=PriceTemplate.TemplateType.DEFAULT,
            background_image=_tiny_png(),
            plan=PLAN_GOLD,
        )
        r = self.client.get(f"/api/auth/programmer/users/{self.staff.pk}/")
        self.assertEqual(r.status_code, 200, r.content)
        data = r.json()
        self.assertEqual(data["user"]["id"], self.staff.pk)
        self.assertEqual(len(data["bots"]), 1)
        self.assertIn("…", data["bots"][0]["token_masked"])
        self.assertEqual(len(data["audit_logs"]), 1)
        price_names = {row["name"] for row in data["templates"]["price_templates"]}
        self.assertIn("Gold board", price_names)
        self.assertNotIn("telegram_analytics", data)

    def test_impersonate_and_nested_denied(self):
        self.client.force_authenticate(self.programmer)
        r = self.client.post(f"/api/auth/impersonate/{self.staff.pk}/")
        self.assertEqual(r.status_code, 200, r.content)
        access = r.json()["access"]
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.programmer,
                action_type=UserActivityLog.ACTION_IMPERSONATE_START,
            ).exists()
        )
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["username"], "desk")
        self.assertEqual(me.json()["impersonated_by"]["username"], "dev")
        nested = self.client.post(f"/api/auth/impersonate/{self.employee.pk}/")
        self.assertIn(nested.status_code, (400, 403))

    def test_cannot_impersonate_self(self):
        self.client.force_authenticate(self.programmer)
        r = self.client.post(f"/api/auth/impersonate/{self.programmer.pk}/")
        self.assertEqual(r.status_code, 400)

    def test_legacy_plan_user_can_fetch_gold_template(self):
        # Rows still carrying a retired tier must resolve to Gold.
        CustomUser.objects.filter(pk=self.staff.pk).update(plan="bronze")
        self.staff.refresh_from_db()
        gold_tpl = PriceTemplate.objects.create(
            name="Gold board",
            template_type=PriceTemplate.TemplateType.DEFAULT,
            background_image=_tiny_png(),
            plan=PLAN_GOLD,
        )
        self.client.force_authenticate(self.staff)
        listed = self.client.get("/api/templates/")
        self.assertEqual(listed.status_code, 200)
        payload = listed.json()
        rows = payload if isinstance(payload, list) else payload.get("results", [])
        self.assertIn(gold_tpl.id, {row["id"] for row in rows})
        ok = self.client.get(f"/api/templates/{gold_tpl.id}/")
        self.assertEqual(ok.status_code, 200)


class ProgrammerDelegatedOperatorApiTests(APITestCase):
    """Registering/editing delegated sub-operators via the Programmer Hub."""

    def setUp(self):
        self.programmer = CustomUser.objects.create_user(
            username="dev2",
            password="pass12345",
            role=CustomUser.ROLE_DEVELOPER,
        )
        self.owner = CustomUser.objects.create_user(
            username="owner_client",
            password="pass12345",
            role=CustomUser.ROLE_MANAGEMENT,
            plan=PLAN_GOLD,
        )
        self.bot = TelegramBot.objects.create(
            name="Owner Bot",
            token="333:owner-bot-token",
            owner=self.owner,
            is_active=True,
        )

    def _register_payload(self, **overrides):
        payload = {
            "first_name": "Sub",
            "last_name": "Operator",
            "exchange_name": "Sub FX",
            "country": "IR",
            "email": "subop@example.com",
            "phone": "+98911",
            "telegram_id": "999000111",
            "telegram_username": "subop_tg",
            "sub_role": CustomUser.SUB_ROLE_OPERATOR,
            "owner_username": "owner_client",
        }
        payload.update(overrides)
        return payload

    def test_register_delegated_operator(self):
        self.client.force_authenticate(self.programmer)
        r = self.client.post(
            "/api/auth/programmer/users/", self._register_payload(), format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)
        data = r.json()
        self.assertEqual(data["role"], CustomUser.ROLE_EMPLOYEE)
        self.assertEqual(data["sub_role"], CustomUser.SUB_ROLE_OPERATOR)
        self.assertEqual(data["owner"], self.owner.pk)
        self.assertEqual(data["owner_name"], "owner_client")
        self.assertEqual(data["telegram_username"], "subop_tg")

        user = CustomUser.objects.get(email="subop@example.com")
        self.assertEqual(user.owner_id, self.owner.pk)
        # No bot is created for delegated operators (they use the owner's bot).
        self.assertFalse(TelegramBot.objects.filter(owner=user).exists())

    def test_register_client_account_still_requires_bot_token(self):
        self.client.force_authenticate(self.programmer)
        payload = self._register_payload(sub_role=CustomUser.SUB_ROLE_ADMIN, owner_username="")
        r = self.client.post("/api/auth/programmer/users/", payload, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("telegram_bot_token", r.json()["errors"])

    def test_register_delegated_operator_requires_owner(self):
        self.client.force_authenticate(self.programmer)
        payload = self._register_payload(owner_username="")
        r = self.client.post("/api/auth/programmer/users/", payload, format="json")
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("owner_username", r.json()["errors"])

    def test_update_operator_owner_and_sub_role(self):
        user = CustomUser.objects.create_user(
            username="existing_op",
            password="pass12345",
            role=CustomUser.ROLE_EMPLOYEE,
            sub_role=CustomUser.SUB_ROLE_ADMIN,
        )
        self.client.force_authenticate(self.programmer)
        r = self.client.patch(
            f"/api/auth/programmer/users/{user.pk}/",
            {
                "sub_role": CustomUser.SUB_ROLE_HEAD_OPERATOR,
                "owner_username": "owner_client",
                "telegram_username": "existing_op_tg",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        user.refresh_from_db()
        self.assertEqual(user.sub_role, CustomUser.SUB_ROLE_HEAD_OPERATOR)
        self.assertEqual(user.owner_id, self.owner.pk)
        self.assertEqual(user.telegram_username, "existing_op_tg")

    def test_update_clears_owner_when_username_empty(self):
        user = CustomUser.objects.create_user(
            username="op_to_revoke",
            password="pass12345",
            role=CustomUser.ROLE_EMPLOYEE,
            sub_role=CustomUser.SUB_ROLE_OPERATOR,
            owner=self.owner,
        )
        self.client.force_authenticate(self.programmer)
        r = self.client.patch(
            f"/api/auth/programmer/users/{user.pk}/",
            {"owner_username": "", "sub_role": CustomUser.SUB_ROLE_ADMIN},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.content)
        user.refresh_from_db()
        self.assertIsNone(user.owner)


class AdminManagementTeamApiTests(APITestCase):
    """Owners add their own bot operators from Admin Management (/users)."""

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="desk_owner", password="pass12345",
            role=CustomUser.ROLE_MANAGEMENT, plan=PLAN_GOLD,
        )
        self.bot = TelegramBot.objects.create(
            name="Desk Bot", token="444:desk", owner=self.owner, is_active=True,
        )
        self.other_owner = CustomUser.objects.create_user(
            username="rival_owner", password="pass12345", role=CustomUser.ROLE_MANAGEMENT,
        )
        self.rival_op = CustomUser.objects.create_user(
            username="rival_op", password="pass12345", role=CustomUser.ROLE_EMPLOYEE,
            owner=self.other_owner, sub_role=CustomUser.SUB_ROLE_OPERATOR,
            telegram_username="rival_tg",
        )

    def _create(self, **overrides):
        payload = {
            "username": "desk_op", "password": "pass12345",
            "sub_role": CustomUser.SUB_ROLE_HEAD_OPERATOR, "telegram_username": "@desk_tg",
        }
        payload.update(overrides)
        return self.client.post("/api/auth/users/", payload, format="json")

    def test_owner_creates_operator_with_fixed_role_and_owner(self):
        self.client.force_authenticate(self.owner)
        r = self._create(role=CustomUser.ROLE_SUPER_ADMIN)
        self.assertEqual(r.status_code, 201, r.content)
        op = CustomUser.objects.get(username="desk_op")
        self.assertEqual(op.role, CustomUser.ROLE_EMPLOYEE)
        self.assertEqual(op.owner_id, self.owner.pk)
        self.assertEqual(op.account_id, self.owner.account_id)
        self.assertEqual(op.sub_role, CustomUser.SUB_ROLE_HEAD_OPERATOR)
        self.assertEqual(op.telegram_username, "desk_tg")

    def test_owner_sees_and_edits_only_own_operators(self):
        self.client.force_authenticate(self.owner)
        self._create()
        names = {u["username"] for u in self.client.get("/api/auth/users/").json()}
        self.assertEqual(names, {"desk_op"})
        r = self.client.patch(f"/api/auth/users/{self.rival_op.pk}/", {"full_name": "x"}, format="json")
        self.assertEqual(r.status_code, 404)
        r = self.client.post(f"/api/auth/users/{self.rival_op.pk}/force-logout/")
        self.assertEqual(r.status_code, 404)

    def test_owner_cannot_escalate_operator_role(self):
        self.client.force_authenticate(self.owner)
        self._create()
        op = CustomUser.objects.get(username="desk_op")
        r = self.client.patch(
            f"/api/auth/users/{op.pk}/", {"role": CustomUser.ROLE_SUPER_ADMIN}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)
        op.refresh_from_db()
        self.assertEqual(op.role, CustomUser.ROLE_EMPLOYEE)

    def test_owner_position_must_be_operator_or_head(self):
        self.client.force_authenticate(self.owner)
        r = self._create(sub_role=CustomUser.SUB_ROLE_ADMIN)
        self.assertEqual(r.status_code, 400, r.content)

    def test_telegram_identity_cannot_be_reused_across_desks(self):
        self.client.force_authenticate(self.owner)
        r = self._create(telegram_username="RIVAL_TG")
        self.assertEqual(r.status_code, 400, r.content)

    def test_employee_manages_users_like_management(self):
        """An employee creates operators under its own desk owner, same as management."""
        self.client.force_authenticate(self.rival_op)
        r = self._create()
        self.assertEqual(r.status_code, 201, r.content)
        created = CustomUser.objects.get(username="desk_op")
        self.assertEqual(created.owner_id, (self.rival_op.owner or self.rival_op).pk)
        self.assertEqual(created.role, CustomUser.ROLE_EMPLOYEE)

    def test_super_admin_operator_requires_owner(self):
        admin = CustomUser.objects.create_user(
            username="root", password="pass12345", role=CustomUser.ROLE_SUPER_ADMIN,
        )
        self.client.force_authenticate(admin)
        r = self._create(role=CustomUser.ROLE_EMPLOYEE)
        self.assertEqual(r.status_code, 400, r.content)
        r = self._create(role=CustomUser.ROLE_EMPLOYEE, owner_username="desk_owner")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(CustomUser.objects.get(username="desk_op").owner_id, self.owner.pk)


class AdminRoleChangeTests(APITestCase):
    """Super admins promote users to admin and back from Admin Management."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username="root", password="pass12345", role=CustomUser.ROLE_SUPER_ADMIN,
        )
        self.staff = CustomUser.objects.create_user(
            username="staff", password="pass12345", role=CustomUser.ROLE_MANAGEMENT,
        )
        self.client.force_authenticate(self.admin)

    def _set_role(self, user, role, **extra):
        return self.client.patch(
            f"/api/auth/users/{user.pk}/", {"role": role, **extra}, format="json"
        )

    def test_promote_user_to_admin(self):
        r = self._set_role(self.staff, CustomUser.ROLE_SUPER_ADMIN, sub_role=CustomUser.SUB_ROLE_ADMIN)
        self.assertEqual(r.status_code, 200, r.content)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.role, CustomUser.ROLE_SUPER_ADMIN)

    def test_promote_operator_to_admin(self):
        op = CustomUser.objects.create_user(
            username="op", password="pass12345", role=CustomUser.ROLE_EMPLOYEE,
            owner=self.staff, sub_role=CustomUser.SUB_ROLE_OPERATOR,
        )
        r = self._set_role(op, CustomUser.ROLE_SUPER_ADMIN, sub_role=CustomUser.SUB_ROLE_ADMIN)
        self.assertEqual(r.status_code, 200, r.content)
        op.refresh_from_db()
        self.assertEqual(op.role, CustomUser.ROLE_SUPER_ADMIN)

    def test_demotion_also_clears_superuser_flag(self):
        other = CustomUser.objects.create_superuser(
            username="legacy", password="pass12345", role=CustomUser.ROLE_SUPER_ADMIN,
        )
        r = self._set_role(other, CustomUser.ROLE_MANAGEMENT)
        self.assertEqual(r.status_code, 200, r.content)
        other.refresh_from_db()
        self.assertEqual(other.role, CustomUser.ROLE_MANAGEMENT)
        self.assertFalse(other.is_superuser)
        self.assertFalse(other.is_staff)

    def test_admin_cannot_demote_themselves(self):
        r = self._set_role(self.admin, CustomUser.ROLE_MANAGEMENT)
        self.assertEqual(r.status_code, 400, r.content)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, CustomUser.ROLE_SUPER_ADMIN)

    def test_management_cannot_promote(self):
        op = CustomUser.objects.create_user(
            username="op", password="pass12345", role=CustomUser.ROLE_EMPLOYEE,
            owner=self.staff, sub_role=CustomUser.SUB_ROLE_OPERATOR,
        )
        self.client.force_authenticate(self.staff)
        r = self._set_role(op, CustomUser.ROLE_SUPER_ADMIN)
        self.assertEqual(r.status_code, 200, r.content)
        op.refresh_from_db()
        self.assertEqual(op.role, CustomUser.ROLE_EMPLOYEE)


class SelfServeSignupTests(APITestCase):
    """Signup must hand back a usable session and a running trial in one call."""

    SIGNUP_URL = "/api/auth/signup/"

    def _payload(self, **overrides):
        payload = {
            "email": "owner@exchange.test",
            "password": "correct-horse-9",
            "first_name": "Sara",
            "last_name": "Ahmadi",
            "exchange_name": "Sara Exchange",
        }
        payload.update(overrides)
        return payload

    def test_signup_creates_a_management_account_on_a_running_trial(self):
        r = self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertTrue(body["access"])
        self.assertTrue(body["refresh"])

        user = CustomUser.objects.get(email="owner@exchange.test")
        self.assertEqual(user.role, CustomUser.ROLE_MANAGEMENT)
        self.assertEqual(user.sub_role, CustomUser.SUB_ROLE_ADMIN)
        self.assertEqual(user.plan, PLAN_GOLD)
        self.assertIsNotNone(user.trial_started_at)
        self.assertIsNotNone(user.trial_expires_at)
        self.assertIsNone(user.registered_by)
        self.assertEqual(
            (user.trial_expires_at - user.trial_started_at).days,
            settings.INDIVIDUAL_TRIAL_DAYS,
        )

    def test_signup_grants_panel_access_before_the_email_is_verified(self):
        r = self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.json()["user"]["email_verified_at"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["email"], "owner@exchange.test")

    def test_signup_sends_a_verification_email_that_verifies_once(self):
        mail.outbox = []
        r = self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("owner@exchange.test", mail.outbox[0].to)

        user = CustomUser.objects.get(email="owner@exchange.test")
        token = make_verification_token(user)
        confirm = self.client.post(
            "/api/auth/verify-email/", {"token": token}, format="json"
        )
        self.assertEqual(confirm.status_code, 200, confirm.content)
        user.refresh_from_db()
        self.assertIsNotNone(user.email_verified_at)

    def test_a_tampered_or_unknown_token_is_rejected(self):
        r = self.client.post(
            "/api/auth/verify-email/", {"token": "not-a-real-token"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "verification_invalid")

    def test_changing_the_email_invalidates_an_outstanding_link(self):
        self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        user = CustomUser.objects.get(email="owner@exchange.test")
        token = make_verification_token(user)

        user.email = "moved@exchange.test"
        user.save(update_fields=["email"])

        r = self.client.post("/api/auth/verify-email/", {"token": token}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_a_taken_email_is_refused(self):
        self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        r = self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("email", r.json().get("errors", {}))

    def test_a_weak_password_is_refused(self):
        r = self.client.post(
            self.SIGNUP_URL, self._payload(password="12345678"), format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("password", r.json().get("errors", {}))

    @override_settings(SIGNUP_ENABLED=False)
    def test_signup_can_be_switched_off_per_install(self):
        r = self.client.post(self.SIGNUP_URL, self._payload(), format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "signup_disabled")


class SettingsAccessTests(APITestCase):
    """The workspace owner configures the workspace; the rest stays super-admin."""

    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            username="owner", password="pass12345", role=CustomUser.ROLE_MANAGEMENT
        )
        self.employee = CustomUser.objects.create_user(
            username="clerk", password="pass12345", role=CustomUser.ROLE_EMPLOYEE
        )
        self.admin = CustomUser.objects.create_user(
            username="boss", password="pass12345", role=CustomUser.ROLE_SUPER_ADMIN
        )

    def test_owner_can_save_site_settings(self):
        self.client.force_authenticate(self.owner)
        r = self.client.put(
            "/api/settings/site/", {"site_name": "Sara Exchange"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)

    def test_employee_can_save_site_settings_like_management(self):
        self.client.force_authenticate(self.employee)
        r = self.client.put(
            "/api/settings/site/", {"site_name": "Clerk Exchange"}, format="json"
        )
        self.assertEqual(r.status_code, 200, r.content)

    def test_activity_log_is_open_to_the_owner_but_scoped_to_its_team(self):
        """A desk owner and an employee both audit the desk's operators."""
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/auth/activity/").status_code, 200)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/auth/activity/").status_code, 200)
        self.client.force_authenticate(self.employee)
        self.assertEqual(self.client.get("/api/auth/activity/").status_code, 200)
