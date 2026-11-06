"""Email login, Google sign-in and the read-only trial wall."""
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import CustomUser, UserActivityLog
from accounts.scoping import unscoped
from category.models import Category


def _signup(**overrides):
    fields = {
        "username": "desk",
        "password": "pass12345",
        "role": CustomUser.ROLE_MANAGEMENT,
        "email": "desk@example.com",
    }
    fields.update(overrides)
    with unscoped():
        return CustomUser.objects.create_user(**fields)


class EmailLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = _signup()

    def test_login_with_email(self):
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "desk@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["user"]["username"], "desk")

    def test_login_with_email_is_case_insensitive(self):
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "DESK@Example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)

    def test_username_login_still_works(self):
        r = self.client.post(
            "/api/auth/login/", {"username": "desk", "password": "pass12345"}, format="json"
        )
        self.assertEqual(r.status_code, 200)

    def test_wrong_password_is_rejected_and_logged(self):
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "desk@example.com", "password": "nope"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        with unscoped():
            self.assertTrue(
                UserActivityLog.objects.filter(
                    action_type=UserActivityLog.ACTION_LOGIN_FAILED
                ).exists()
            )

    def test_an_expired_trial_can_still_sign_in(self):
        self.user.trial_started_at = timezone.now() - timezone.timedelta(days=30)
        self.user.trial_expires_at = timezone.now() - timezone.timedelta(days=1)
        self.user.save(update_fields=["trial_started_at", "trial_expires_at"])
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "desk@example.com", "password": "pass12345"},
            format="json",
        )
        self.assertEqual(r.status_code, 200)


class TrialWallTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = _signup()
        self.user.trial_started_at = timezone.now() - timezone.timedelta(days=30)
        self.user.trial_expires_at = timezone.now() - timezone.timedelta(days=1)
        self.user.save(update_fields=["trial_started_at", "trial_expires_at"])
        tokens = self.client.post(
            "/api/auth/login/",
            {"identifier": "desk@example.com", "password": "pass12345"},
            format="json",
        ).json()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_reads_still_work(self):
        self.assertEqual(self.client.get("/api/categories/").status_code, 200)

    def test_writes_are_walled_with_support_channels(self):
        r = self.client.post("/api/categories/", {"name": "Gold"}, format="json")
        self.assertEqual(r.status_code, 403)
        body = r.json()
        self.assertEqual(body["code"], "trial_expired")
        self.assertIn("support_channels", body)
        with unscoped():
            self.assertFalse(Category.all_objects.filter(name="Gold").exists())


_CLAIMS = {
    "sub": "google-sub-1",
    "email": "new@example.com",
    "email_verified": True,
    "given_name": "New",
    "family_name": "Customer",
}


@override_settings(GOOGLE_OAUTH_CLIENT_ID="client-id.apps.googleusercontent.com")
class GoogleAuthTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_disabled_without_a_client_id(self):
        with override_settings(GOOGLE_OAUTH_CLIENT_ID=""):
            r = self.client.post("/api/auth/google/", {"credential": "x"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["code"], "google_auth_disabled")

    @patch("accounts.api_views.verify_id_token", return_value=None)
    def test_an_unverifiable_token_is_rejected(self, _verify):
        r = self.client.post("/api/auth/google/", {"credential": "forged"}, format="json")
        self.assertEqual(r.status_code, 401)

    @patch("accounts.api_views.verify_id_token", return_value=_CLAIMS)
    def test_a_new_google_user_gets_their_own_verified_account(self, _verify):
        r = self.client.post("/api/auth/google/", {"credential": "ok"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.json()["created"])
        with unscoped():
            user = CustomUser.objects.get(email="new@example.com")
        self.assertEqual(user.google_sub, "google-sub-1")
        self.assertIsNotNone(user.email_verified_at)
        self.assertIsNotNone(user.trial_expires_at)
        self.assertFalse(user.has_usable_password())
        self.assertIsNotNone(user.account_id)

    @patch("accounts.api_views.verify_id_token", return_value=_CLAIMS)
    def test_an_existing_password_account_is_linked_not_duplicated(self, _verify):
        existing = _signup(username="existing", email="new@example.com")
        r = self.client.post("/api/auth/google/", {"credential": "ok"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["created"])
        existing.refresh_from_db()
        self.assertEqual(existing.google_sub, "google-sub-1")
        with unscoped():
            self.assertEqual(CustomUser.objects.filter(email="new@example.com").count(), 1)

    @patch(
        "accounts.api_views.verify_id_token",
        return_value={**_CLAIMS, "email_verified": True, "sub": "google-sub-2"},
    )
    def test_signing_in_twice_reuses_the_same_account(self, _verify):
        self.client.post("/api/auth/google/", {"credential": "ok"}, format="json")
        r = self.client.post("/api/auth/google/", {"credential": "ok"}, format="json")
        self.assertEqual(r.status_code, 200)
        with unscoped():
            self.assertEqual(CustomUser.objects.filter(email="new@example.com").count(), 1)


class RememberMeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = _signup()

    def _login(self, **extra):
        r = self.client.post(
            "/api/auth/login/",
            {"identifier": "desk", "password": "pass12345", **extra},
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        return r.json()

    @staticmethod
    def _lifetime_days(token):
        from rest_framework_simplejwt.tokens import RefreshToken

        t = RefreshToken(token)
        return round((t["exp"] - t["iat"]) / 86400)

    def test_default_login_keeps_standard_lifetime(self):
        self.assertEqual(self._lifetime_days(self._login()["refresh"]), 7)

    def test_remember_me_extends_refresh_lifetime(self):
        self.assertEqual(self._lifetime_days(self._login(remember_me=True)["refresh"]), 30)

    def test_remember_me_survives_token_rotation(self):
        refresh = self._login(remember_me=True)["refresh"]
        r = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self._lifetime_days(r.json()["refresh"]), 30)
