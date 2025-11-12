from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from telegram_app.forms import SendMessageForm, TelegramBotForm, TelegramChannelForm
from telegram_app.models import TelegramBot, TelegramChannel
from telegram_app.services.telegram_client import TelegramService


@require_http_methods(["GET", "POST"])
def settings_view(request):
    """
    Main settings view that displays all settings sections.
    Includes Telegram bot and channel management, and message sending.
    """
    # Initialize forms
    telegram_form = SendMessageForm(request.POST or None)
    bot_form = TelegramBotForm(request.POST or None)
    channel_form = TelegramChannelForm(request.POST or None)
    
    # Get all bots and channels for display
    bots = TelegramBot.objects.all().order_by('-created_at')
    channels = TelegramChannel.objects.select_related('bot').all().order_by('-created_at')
    
    # Handle Telegram message form submission
    if request.method == "POST":
        form_type = request.POST.get('form_type')
        
        if form_type == 'send_message':
            if telegram_form.is_valid():
                bot = telegram_form.cleaned_data['bot']
                channel = telegram_form.cleaned_data['channel']
                message = telegram_form.cleaned_data['message']

                try:
                    client = TelegramService(bot.token)
                    success, response = client.send_message(channel.chat_id, message)

                    if success:
                        messages.success(request, response)
                        telegram_form = SendMessageForm()  # Reset form on success
                    else:
                        messages.error(request, f"Failed to send message: {response}")
                except Exception as e:
                    messages.error(request, f"An error occurred: {str(e)}")
            else:
                messages.error(request, "Please correct the errors in the message form.")
        
        elif form_type == 'add_bot':
            bot_form = TelegramBotForm(request.POST)
            if bot_form.is_valid():
                bot_form.save()
                messages.success(request, f"Bot '{bot_form.cleaned_data['name']}' has been added successfully!")
                return redirect('setting:settings')
            else:
                messages.error(request, "Please correct the errors in the bot form.")
        
        elif form_type == 'add_channel':
            channel_form = TelegramChannelForm(request.POST)
            if channel_form.is_valid():
                channel_form.save()
                messages.success(request, f"Channel '{channel_form.cleaned_data['name']}' has been added successfully!")
                return redirect('setting:settings')
            else:
                messages.error(request, "Please correct the errors in the channel form.")

    context = {
        'telegram_form': telegram_form,
        'bot_form': bot_form,
        'channel_form': channel_form,
        'bots': bots,
        'channels': channels,
    }
    
    return render(request, "setting/settings.html", context)


@require_http_methods(["GET", "POST"])
def edit_bot(request, bot_id):
    """Edit an existing Telegram bot."""
    bot = get_object_or_404(TelegramBot, id=bot_id)
    
    if request.method == "POST":
        form = TelegramBotForm(request.POST, instance=bot)
        if form.is_valid():
            form.save()
            messages.success(request, f"Bot '{form.cleaned_data['name']}' has been updated successfully!")
            return redirect('setting:settings')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = TelegramBotForm(instance=bot)
    
    context = {
        'form': form,
        'bot': bot,
        'form_type': 'bot'
    }
    
    return render(request, "setting/edit_form.html", context)


@require_http_methods(["GET", "POST"])
def edit_channel(request, channel_id):
    """Edit an existing Telegram channel."""
    channel = get_object_or_404(TelegramChannel, id=channel_id)
    
    if request.method == "POST":
        form = TelegramChannelForm(request.POST, instance=channel)
        if form.is_valid():
            form.save()
            messages.success(request, f"Channel '{form.cleaned_data['name']}' has been updated successfully!")
            return redirect('setting:settings')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = TelegramChannelForm(instance=channel)
    
    context = {
        'form': form,
        'channel': channel,
        'form_type': 'channel'
    }
    
    return render(request, "setting/edit_form.html", context)


@require_http_methods(["POST"])
def delete_bot(request, bot_id):
    """Delete a Telegram bot."""
    bot = get_object_or_404(TelegramBot, id=bot_id)
    bot_name = bot.name
    
    # Delete associated channels first (CASCADE will handle this automatically)
    bot.delete()
    messages.success(request, f"Bot '{bot_name}' and its associated channels have been deleted successfully!")
    
    return redirect('setting:settings')


@require_http_methods(["POST"])
def delete_channel(request, channel_id):
    """Delete a Telegram channel."""
    channel = get_object_or_404(TelegramChannel, id=channel_id)
    channel_name = channel.name
    
    channel.delete()
    messages.success(request, f"Channel '{channel_name}' has been deleted successfully!")
    
    return redirect('setting:settings')