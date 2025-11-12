from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import DefaultMessageSettingsForm, SendMessageForm
from .models import DefaultMessageSettings
from .services.telegram_client import TelegramService


@require_http_methods(["GET", "POST"])
def send_message_view(request):
    """
    View for sending messages to Telegram channels.
    """
    form = SendMessageForm(request.POST or None)
    
    if request.method == "POST":
        if form.is_valid():
            bot = form.cleaned_data['bot']
            channel = form.cleaned_data['channel']
            message = form.cleaned_data['message']

            try:
                client = TelegramService(bot.token)
                success, response = client.send_message(channel.chat_id, message)

                if success:
                    messages.success(request, response)
                    form = SendMessageForm()  # Reset form on success
                else:
                    messages.error(request, f"Failed to send message: {response}")
            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, "telegram_app/send_message.html", {"form": form})


@staff_member_required
@require_http_methods(["GET", "POST"])
def default_settings_view(request):
    """
    Manage default message settings per bot with preview support.
    """
    selected_bot_id = request.GET.get("bot") or request.POST.get("bot")
    settings_instance = None
    if selected_bot_id:
        settings_instance = (
            DefaultMessageSettings.objects.filter(bot_id=selected_bot_id)
            .order_by("-active", "-updated_at")
            .first()
        )

    initial = {}
    if selected_bot_id:
        initial["bot"] = selected_bot_id
    form = DefaultMessageSettingsForm(
        request.POST or None,
        instance=settings_instance,
        initial=initial if not request.POST else None,
    )
    preview_payload = None
    preview_result = None

    if request.method == "POST":
        action = request.POST.get("action")
        if form.is_valid():
            instance = form.save(commit=False)
            instance.default_buttons = form.cleaned_data["default_buttons"]
            preview_channel = form.cleaned_data.get("preview_channel")

            if action == "preview" or action == "preview_send":
                preview_payload = {
                    "caption": instance.default_caption,
                    "buttons": instance.default_buttons,
                    "bot": instance.bot,
                }
                if action == "preview_send":
                    if preview_channel:
                        try:
                            client = TelegramService(instance.bot.token)
                            success, detail = client.send_message(
                                chat_id=preview_channel.chat_id,
                                text=instance.default_caption or "Preview caption",
                                buttons=instance.default_buttons,
                            )
                        except Exception as exc:  # pragma: no cover - defensive
                            success = False
                            detail = str(exc)
                        preview_result = {
                            "success": success,
                            "detail": detail,
                            "channel": preview_channel.chat_id,
                        }
                        if success:
                            messages.success(
                                request,
                                f"Preview sent to {preview_channel.chat_id}: {detail}",
                            )
                        else:
                            messages.error(
                                request,
                                f"Failed to send preview to {preview_channel.chat_id}: {detail}",
                            )
                    else:
                        messages.warning(
                            request,
                            "Select a preview channel to send the preview message.",
                        )
            else:
                instance.save()
                messages.success(
                    request,
                    "Default message settings saved successfully.",
                )
                return redirect(f"{request.path}?bot={instance.bot_id}")
        else:
            messages.error(request, "Please fix the errors below.")

    context = {
        "form": form,
        "preview": preview_payload,
        "preview_result": preview_result,
    }
    return render(request, "telegram_app/default_settings.html", context)
