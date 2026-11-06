"""Support-channel payloads shared by the API, the trial wall and templates."""


def support_channel_payload():
    """Active support channels, newest config, safe to call from anywhere.

    Returns a plain list of dicts rather than model instances so it can be
    dropped straight into a ``JsonResponse`` — including from middleware, which
    runs outside DRF and has no serializer context.

    Never raises: this is called from the expired-trial wall, and a database
    hiccup there must not turn a clear "your trial ended" message into a 500.
    """
    try:
        from .models import SupportChannel

        return [
            {
                "kind": channel.kind,
                "label": channel.label,
                "value": channel.value,
                "icon": channel.display_icon,
                "href": channel.href,
            }
            for channel in SupportChannel.objects.filter(is_active=True)
        ]
    except Exception:
        return []
