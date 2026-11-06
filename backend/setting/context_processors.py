from setting.models import SiteSettings


def site_settings_processor(request):
    return {"site_settings": SiteSettings.load()}
