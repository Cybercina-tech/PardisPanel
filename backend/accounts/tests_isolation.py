"""Cross-account isolation acceptance tests.

Two desks share one deployment. Everything here asserts that neither can read
or write the other's rows, which is the guarantee the whole scoping layer
exists to provide — a regression here is a customer data breach, not a bug.
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from accounts.scoping import act_as_account, unscoped
from category.models import Category, Currency, PriceType
from price_publisher.models import PriceTemplate
from telegram_app.models import TelegramBot, TelegramChannel


_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_desk(username):
    """A management user on an account of their own, plus that account's id."""
    with unscoped():
        user = CustomUser.objects.create_user(
            username=username,
            password="pass12345",
            role=CustomUser.ROLE_MANAGEMENT,
            email=f"{username}@example.com",
        )
    return user, user.account_id


class AccountIsolationTests(APITestCase):
    def setUp(self):
        self.alice, self.alice_account = _make_desk("alice")
        self.bob, self.bob_account = _make_desk("bob")
        self.assertNotEqual(self.alice_account, self.bob_account)

        # Currencies are deliberately global, shared by every desk.
        self.usd, _ = Currency.objects.get_or_create(code="USD", defaults={"name": "Dollar"})
        self.irr, _ = Currency.objects.get_or_create(code="IRR", defaults={"name": "Rial"})

        with act_as_account(self.alice_account):
            self.alice_category = Category.objects.create(name="Alice Gold")
            self.alice_price_type = PriceType.objects.create(
                category=self.alice_category,
                name="Spot",
                trade_type="buy",
                source_currency=self.usd,
                target_currency=self.irr,
            )
            self.alice_template = PriceTemplate.objects.create(
                name="Alice Board",
                background_image=SimpleUploadedFile(
                    "bg.png", _TINY_PNG, content_type="image/png"
                ),
            )
            self.alice_bot = TelegramBot.objects.create(
                name="Alice Bot", token="111:alice", is_active=True
            )
            self.alice_channel = TelegramChannel.objects.create(
                bot=self.alice_bot, name="Alice Channel", chat_id="@alice", is_active=True
            )

        with act_as_account(self.bob_account):
            self.bob_category = Category.objects.create(name="Bob Gold")
            self.bob_bot = TelegramBot.objects.create(
                name="Bob Bot", token="222:bob", is_active=True
            )

    # --- reads ---------------------------------------------------------

    def test_manager_hides_other_accounts_rows(self):
        with act_as_account(self.bob_account):
            self.assertEqual(
                list(Category.objects.values_list("name", flat=True)), ["Bob Gold"]
            )
            self.assertFalse(PriceTemplate.objects.exists())
            self.assertEqual(
                list(TelegramBot.objects.values_list("name", flat=True)), ["Bob Bot"]
            )

    def test_category_list_only_returns_own_rows(self):
        self.client.force_authenticate(self.bob)
        body = self.client.get("/api/categories/").json()
        items = body["results"] if isinstance(body, dict) and "results" in body else body
        self.assertEqual([item["name"] for item in items], ["Bob Gold"])

    def test_category_detail_of_another_account_is_404(self):
        self.client.force_authenticate(self.bob)
        r = self.client.get(f"/api/categories/{self.alice_category.pk}/")
        self.assertEqual(r.status_code, 404)

    def test_nested_price_types_of_another_account_are_hidden(self):
        self.client.force_authenticate(self.bob)
        body = self.client.get(
            f"/api/categories/{self.alice_category.pk}/price-types/"
        ).json()
        items = body["results"] if isinstance(body, dict) and "results" in body else body
        self.assertEqual(items, [])

    def test_template_list_only_returns_own_rows(self):
        self.client.force_authenticate(self.bob)
        body = self.client.get("/api/templates/").json()
        items = body["results"] if isinstance(body, dict) and "results" in body else body
        self.assertEqual(items, [])

    def test_unscoped_request_sees_nothing(self):
        """Scoping fails closed: no account in context yields no rows."""
        with act_as_account(None):
            self.assertFalse(Category.objects.exists())

    # --- writes --------------------------------------------------------

    def test_cannot_update_another_accounts_category(self):
        self.client.force_authenticate(self.bob)
        r = self.client.patch(
            f"/api/categories/{self.alice_category.pk}/", {"name": "Stolen"}, format="json"
        )
        self.assertEqual(r.status_code, 404)
        with unscoped():
            self.assertEqual(
                Category.all_objects.get(pk=self.alice_category.pk).name, "Alice Gold"
            )

    def test_cannot_delete_another_accounts_category(self):
        self.client.force_authenticate(self.bob)
        r = self.client.delete(f"/api/categories/{self.alice_category.pk}/")
        self.assertEqual(r.status_code, 404)
        with unscoped():
            self.assertTrue(Category.all_objects.filter(pk=self.alice_category.pk).exists())

    def test_cannot_attach_a_price_type_to_another_accounts_category(self):
        self.client.force_authenticate(self.bob)
        r = self.client.post(
            f"/api/categories/{self.alice_category.pk}/price-types/",
            {
                "name": "Injected",
                "trade_type": "buy",
                "source_currency_id": self.usd.pk,
                "target_currency_id": self.irr.pk,
            },
            format="json",
        )
        self.assertIn(r.status_code, (400, 403, 404))
        with unscoped():
            self.assertFalse(PriceType.all_objects.filter(name="Injected").exists())

    def test_related_field_rejects_another_accounts_primary_key(self):
        """The classic leak vector: a foreign pk posted through a relation."""
        self.client.force_authenticate(self.bob)
        r = self.client.post(
            "/api/telegram/send-message/",
            {
                "bot_id": self.alice_bot.pk,
                "channel_id": self.alice_channel.pk,
                "message": "hello",
            },
            format="json",
        )
        self.assertIn(r.status_code, (400, 403))
        if r.status_code == 400:
            self.assertTrue(set(r.json()) & {"bot_id", "channel_id", "errors", "detail"})

    def test_created_rows_are_stamped_with_the_callers_account(self):
        self.client.force_authenticate(self.bob)
        r = self.client.post("/api/categories/", {"name": "Bob Silver"}, format="json")
        self.assertEqual(r.status_code, 201)
        with unscoped():
            created = Category.all_objects.get(pk=r.json()["id"])
        self.assertEqual(created.account_id, self.bob_account)

    def test_the_same_name_is_free_on_each_account(self):
        """Uniqueness is per account, or the second customer cannot name anything."""
        self.client.force_authenticate(self.bob)
        r = self.client.post("/api/categories/", {"name": "Alice Gold"}, format="json")
        self.assertEqual(r.status_code, 201)
