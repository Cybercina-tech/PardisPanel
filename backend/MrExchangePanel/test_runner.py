import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class IsolatedMediaTestRunner(DiscoverRunner):
    """Test runner that keeps uploads out of the working tree.

    Renderers and upload endpoints write straight to MEDIA_ROOT, so running the
    suite against the real one leaves stray files in `public/media/` and can
    overwrite the tracked seed backgrounds the price renderers read. Point
    MEDIA_ROOT at a throwaway copy for the duration of the run instead.

    Goes through override_settings rather than assigning to settings.MEDIA_ROOT
    so the setting_changed receivers reset the cached default_storage location.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._tmp_media_root = Path(tempfile.mkdtemp(prefix="mrexchange-test-media-"))
        source = Path(settings.MEDIA_ROOT)
        if source.is_dir():
            shutil.copytree(source, self._tmp_media_root, dirs_exist_ok=True)
        self._media_override = override_settings(MEDIA_ROOT=str(self._tmp_media_root))
        self._media_override.enable()

    def setup_databases(self, **kwargs):
        result = super().setup_databases(**kwargs)
        # Scoping fails closed, so the suite needs a default account in context
        # before the first fixture is built. See accounts.testing.
        from accounts.testing import create_and_pin_test_account

        create_and_pin_test_account()
        return result

    def teardown_test_environment(self, **kwargs):
        self._media_override.disable()
        shutil.rmtree(self._tmp_media_root, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
