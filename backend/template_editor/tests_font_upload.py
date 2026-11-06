import io
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Account, CustomUser
from template_editor.utils import FONT_ROOT, get_available_fonts


class FontUploadTests(TestCase):
    """A custom font is either accepted or refused with a reason."""

    def setUp(self):
        self.client = APIClient()
        account = Account.objects.create(name="Desk", slug="desk")
        self.owner = CustomUser.objects.create_user(
            username="owner", password="pw", role=CustomUser.ROLE_MANAGEMENT
        )
        self.owner.account = account
        self.owner.save()
        self.client.force_authenticate(self.owner)
        self._added = []

    def tearDown(self):
        for name in self._added:
            path = FONT_ROOT / name
            if path.is_file():
                path.unlink()

    def _post(self, filename, payload):
        res = self.client.post(
            "/api/template-editor/fonts/",
            {"file": SimpleUploadedFile(filename, payload)},
            format="multipart",
        )
        if res.status_code < 300 and res.data.get("filename"):
            self._added.append(res.data["filename"])
        return res

    def _real_font_bytes(self):
        existing = get_available_fonts()
        self.assertTrue(existing, "no bundled font to test with")
        return (FONT_ROOT / existing[0][0]).read_bytes()

    def test_a_desk_owner_can_upload_a_real_font(self):
        res = self._post("My Brand Font.ttf", self._real_font_bytes())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(res.data["filename"].endswith(".ttf"))

    def test_a_renamed_file_is_refused_with_a_reason(self):
        res = self._post("notreally.ttf", b"PK\x03\x04this is a zip, not a font")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["code"], "font_invalid")
        self.assertIn("not a TrueType or OpenType font", res.data["detail"])

    def test_an_unsupported_extension_says_what_to_do(self):
        res = self._post("brand.woff2", b"wOF2anything")
        self.assertEqual(res.status_code, 400)
        self.assertIn(".ttf", res.data["detail"])

    def test_an_empty_file_is_refused(self):
        res = self._post("empty.ttf", b"")
        self.assertEqual(res.status_code, 400)
