from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Account, CustomUser, UserActivityLog


class ManagementAdminAccessTests(TestCase):
    """A desk owner (role=management) can work its own Admin section.

    It used to 403 on the activity log and the panel logs, which are the two
    things the Admin section is made of.
    """

    def setUp(self):
        self.client = APIClient()
        self.account = Account.objects.create(name="Desk A", slug="desk-a")
        self.manager = self._user("mgr-a", CustomUser.ROLE_MANAGEMENT, self.account)
        self.operator = self._user("op-a", CustomUser.ROLE_EMPLOYEE, self.account)
        self.operator.owner = self.manager
        self.operator.save()

        self.other_account = Account.objects.create(name="Desk B", slug="desk-b")
        self.stranger = self._user("mgr-b", CustomUser.ROLE_MANAGEMENT, self.other_account)

    def _user(self, username, role, account):
        user = CustomUser.objects.create_user(username=username, password="pw", role=role)
        user.account = account
        user.save()
        return user

    def test_management_can_read_its_admin_section(self):
        self.client.force_authenticate(self.manager)
        for url in ("/api/auth/users/", "/api/auth/activity/", "/api/settings/logs/"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_activity_log_is_limited_to_the_managers_own_team(self):
        for user in (self.manager, self.operator, self.stranger):
            UserActivityLog.objects.create(
                user=user, action_type=UserActivityLog.ACTION_LOGIN_SUCCESS, ip_address="10.0.0.1"
            )

        self.client.force_authenticate(self.manager)
        res = self.client.get("/api/auth/activity/")
        self.assertEqual(res.status_code, 200)
        rows = res.data["results"] if isinstance(res.data, dict) else res.data
        seen = {row["user_display"] for row in rows}
        self.assertEqual(seen, {"mgr-a", "op-a"})

    def test_employee_still_has_no_admin_access(self):
        self.client.force_authenticate(self.operator)
        self.assertEqual(self.client.get("/api/auth/activity/").status_code, 403)
        self.assertEqual(self.client.get("/api/settings/logs/").status_code, 403)
