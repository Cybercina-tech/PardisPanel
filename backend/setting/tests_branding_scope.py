from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Account, CustomUser


class BrandingScopeTests(TestCase):
    """A logo change reaches the desk that made it and its operators — nobody else."""

    def setUp(self):
        self.client = APIClient()
        self.desk_a = Account.objects.create(name="A", slug="a")
        self.desk_b = Account.objects.create(name="B", slug="b")
        self.owner_a = self._user("owner-a", CustomUser.ROLE_MANAGEMENT, self.desk_a)
        self.operator_a = self._user("op-a", CustomUser.ROLE_EMPLOYEE, self.desk_a)
        self.operator_a.owner = self.owner_a
        self.operator_a.save()
        self.owner_b = self._user("owner-b", CustomUser.ROLE_MANAGEMENT, self.desk_b)

    def _user(self, username, role, account):
        user = CustomUser.objects.create_user(username=username, password="pw", role=role)
        user.account = account
        user.save()
        return user

    def _site_name_as(self, user):
        self.client.force_authenticate(user)
        return self.client.get("/api/settings/site/").data.get("site_name")

    def test_branding_reaches_the_desk_and_its_operators_only(self):
        self.client.force_authenticate(self.owner_a)
        res = self.client.put("/api/settings/site/", {"site_name": "DESK-A"}, format="json")
        self.assertEqual(res.status_code, 200)

        self.assertEqual(self._site_name_as(self.owner_a), "DESK-A")
        self.assertEqual(self._site_name_as(self.operator_a), "DESK-A")
        self.assertNotEqual(self._site_name_as(self.owner_b), "DESK-A")

        # The signed-out login screen keeps the shipped branding.
        self.client.force_authenticate(None)
        self.assertNotEqual(
            self.client.get("/api/settings/site/").data.get("site_name"), "DESK-A"
        )

    def test_an_account_less_user_is_told_rather_than_500ing(self):
        staff = self._user("staff", CustomUser.ROLE_SUPER_ADMIN, None)
        self.client.force_authenticate(staff)
        res = self.client.put("/api/settings/site/", {"site_name": "GLOBAL"}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get("code"), "no_account")
