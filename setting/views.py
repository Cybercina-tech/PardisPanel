from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from telegram_app.forms import SendMessageForm, TelegramBotForm, TelegramChannelForm
from telegram_app.models import TelegramBot, TelegramChannel
from telegram_app.services.telegram_client import TelegramService
from .models import Log
from .utils import log_telegram_event


@require_http_methods(["GET", "POST"])
def settings_view(request):
    """
    Main settings view that displays all settings sections.
    Includes Telegram bot and channel management, and message sending.
    """
    # Get active section from query parameter, default to 'general'
    active_section = request.GET.get('section', 'general')
    
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
                        # Log successful message send
                        log_telegram_event(
                            level='INFO',
                            message=f'Message sent via Settings',
                            details=f'Bot: {bot.name}, Channel: {channel.name} ({channel.chat_id}), Message length: {len(message)} characters',
                            user=request.user if request.user.is_authenticated else None
                        )
                        messages.success(request, response)
                        telegram_form = SendMessageForm()  # Reset form on success
                    else:
                        # Log failed message send
                        log_telegram_event(
                            level='ERROR',
                            message=f'Failed to send message via Settings',
                            details=f'Bot: {bot.name}, Channel: {channel.name} ({channel.chat_id}), Error: {response}',
                            user=request.user if request.user.is_authenticated else None
                        )
                        messages.error(request, f"Failed to send message: {response}")
                except Exception as e:
                    # Log exception
                    log_telegram_event(
                        level='ERROR',
                        message=f'Exception occurred while sending message via Settings',
                        details=f'Bot: {bot.name}, Channel: {channel.name if channel else "Unknown"}, Error: {str(e)}',
                        user=request.user if request.user.is_authenticated else None
                    )
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
        'active_section': active_section,
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


@require_http_methods(["GET"])
def logs_view(request):
    """
    Display application logs from various sources.
    Supports filtering by level, source, and pagination.
    """
    # Get filter parameters
    level_filter = request.GET.get('level', '')
    source_filter = request.GET.get('source', '')
    search_query = request.GET.get('search', '')
    
    # Start with all logs
    logs = Log.objects.select_related('user').all()
    
    # Apply filters
    if level_filter:
        logs = logs.filter(level=level_filter)
    
    if source_filter:
        logs = logs.filter(source=source_filter)
    
    if search_query:
        logs = logs.filter(message__icontains=search_query)
    
    # Pagination
    paginator = Paginator(logs, 50)  # Show 50 logs per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get counts for statistics
    total_logs = Log.objects.count()
    error_logs = Log.objects.filter(level__in=['ERROR', 'CRITICAL']).count()
    warning_logs = Log.objects.filter(level='WARNING').count()
    
    context = {
        'logs': page_obj,
        'level_filter': level_filter,
        'source_filter': source_filter,
        'search_query': search_query,
        'total_logs': total_logs,
        'error_logs': error_logs,
        'warning_logs': warning_logs,
        'level_choices': Log.LEVEL_CHOICES,
        'source_choices': Log.SOURCE_CHOICES,
    }
    
    return render(request, "setting/logs.html", context)