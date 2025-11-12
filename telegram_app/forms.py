from django import forms
import json

from django import forms
from django.core.exceptions import ValidationError

from .models import DefaultMessageSettings, TelegramBot, TelegramChannel


class SendMessageForm(forms.Form):
    """Form for sending messages to Telegram channels."""
    
    bot = forms.ModelChoiceField(
        queryset=TelegramBot.objects.filter(is_active=True),
        empty_label="Select a bot",
        label="Bot",
        help_text="Choose the bot to use for sending the gold message",
        widget=forms.Select(attrs={'class': 'form-select theme-input'})
    )
    channel = forms.ModelChoiceField(
        queryset=TelegramChannel.objects.none(),
        empty_label="Select a channel",
        label="Channel",
        help_text="Choose the channel to send the gold message to",
        widget=forms.Select(attrs={'class': 'form-select theme-input'})
    )
    message = forms.CharField(
        label="Message",
        help_text="Enter the gold message to send",
        widget=forms.Textarea(attrs={
            'rows': 6,
            'class': 'form-control theme-input',
            'placeholder': 'Enter your message here...'
        }),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter channels by active bots and active channels
        self.fields['channel'].queryset = TelegramChannel.objects.filter(
            bot__is_active=True,
            is_active=True
        ).select_related('bot')

    def clean_message(self):
        """Validate that message is not empty or only whitespace."""
        message = self.cleaned_data.get('message', '').strip()
        if not message:
            raise forms.ValidationError("Message cannot be empty or contain only whitespace.")
        return message

    def clean(self):
        """Validate that channel belongs to selected bot."""
        cleaned_data = super().clean()
        bot = cleaned_data.get('bot')
        channel = cleaned_data.get('channel')

        if bot and channel and channel.bot != bot:
            raise forms.ValidationError({
                'channel': "The selected channel does not belong to the selected bot."
            })

        return cleaned_data


class TelegramBotForm(forms.ModelForm):
    """Form for creating and editing Telegram bots."""
    
    class Meta:
        model = TelegramBot
        fields = ['name', 'token', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter bot name'
            }),
            'token': forms.TextInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter bot token from @BotFather'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input theme-input'
            })
        }
        labels = {
            'name': 'Bot Name',
            'token': 'Bot Token',
            'is_active': 'Active'
        }
        help_texts = {
            'name': 'A friendly name for this bot',
            'token': 'Telegram bot token from @BotFather',
            'is_active': 'Whether this bot is currently active'
        }


class TelegramChannelForm(forms.ModelForm):
    """Form for creating and editing Telegram channels."""
    
    class Meta:
        model = TelegramChannel
        fields = ['bot', 'name', 'chat_id', 'is_active']
        widgets = {
            'bot': forms.Select(attrs={
                'class': 'form-select theme-input'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter channel name'
            }),
            'chat_id': forms.TextInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter chat ID (e.g., @channelname or -1001234567890)'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input theme-input'
            })
        }
        labels = {
            'bot': 'Bot',
            'name': 'Channel Name',
            'chat_id': 'Chat ID',
            'is_active': 'Active'
        }
        help_texts = {
            'bot': 'The bot used to send messages to this channel',
            'name': 'A friendly name for this channel',
            'chat_id': 'Telegram channel chat ID (e.g., @channelname or -1001234567890)',
            'is_active': 'Whether this channel is currently active'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all bots (including inactive ones) when editing, but prefer active ones for new channels
        if self.instance and self.instance.pk:
            # Editing: show all bots so user can change bot even if current one is inactive
            self.fields['bot'].queryset = TelegramBot.objects.all()
        else:
            # Creating: only show active bots
            self.fields['bot'].queryset = TelegramBot.objects.filter(is_active=True)
        self.fields['bot'].empty_label = "Select a bot"


class DefaultMessageSettingsForm(forms.ModelForm):
    preview_channel = forms.ModelChoiceField(
        queryset=TelegramChannel.objects.none(),
        required=False,
        label="Preview Channel",
        help_text="Optional channel to send a preview message.",
        widget=forms.Select(attrs={"class": "form-select theme-input"}),
    )
    default_buttons = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "class": "form-control theme-input monospace",
                "placeholder": '[ [{"text": "View", "url": "https://example.com"}] ]',
            }
        ),
        help_text="Enter inline buttons as JSON. Example: [[{\"text\": \"Buy\", \"url\": \"https://...\"}]]",
        label="Default Buttons (JSON)",
    )

    class Meta:
        model = DefaultMessageSettings
        fields = ["bot", "active", "default_caption", "default_buttons"]
        widgets = {
            "bot": forms.Select(attrs={"class": "form-select theme-input"}),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input theme-input"}),
            "default_caption": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control theme-input",
                    "placeholder": "Optional default caption...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_bots = TelegramBot.objects.filter(is_active=True)
        self.fields["bot"].queryset = active_bots

        selected_bot = None
        if self.data.get("bot"):
            selected_bot = active_bots.filter(pk=self.data.get("bot")).first()
        elif self.instance and self.instance.pk:
            selected_bot = self.instance.bot
        elif self.initial.get("bot"):
            selected_bot = active_bots.filter(pk=self.initial.get("bot")).first()

        if selected_bot:
            self.fields["bot"].initial = selected_bot
            self.fields["preview_channel"].queryset = TelegramChannel.objects.filter(
                bot=selected_bot, is_active=True
            )
        else:
            self.fields["preview_channel"].queryset = TelegramChannel.objects.filter(
                is_active=True, bot__is_active=True
            )

        if self.instance and self.instance.default_buttons:
            self.initial.setdefault(
                "default_buttons", json.dumps(self.instance.default_buttons, ensure_ascii=False, indent=2)
            )

    def clean_default_buttons(self):
        buttons_raw = self.cleaned_data.get("default_buttons")
        if not buttons_raw:
            return []
        try:
            parsed = json.loads(buttons_raw)
            if not isinstance(parsed, list):
                raise ValidationError("Buttons JSON must be a list of button rows.")
            for row in parsed:
                if not isinstance(row, list):
                    raise ValidationError("Each row must be a list of button definitions.")
                for button in row:
                    if not isinstance(button, dict):
                        raise ValidationError("Button definitions must be objects.")
                    if "text" not in button:
                        raise ValidationError("Each button requires a 'text' field.")
                    if not any(key in button for key in ("url", "callback_data", "switch_inline_query", "switch_inline_query_current_chat")):
                        raise ValidationError(
                            "Buttons must include one of: url, callback_data, switch_inline_query, switch_inline_query_current_chat."
                        )
            return parsed
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Invalid JSON: {exc}") from exc

    def clean(self):
        cleaned_data = super().clean()
        bot = cleaned_data.get("bot")
        preview_channel = self.cleaned_data.get("preview_channel")
        if preview_channel and bot and preview_channel.bot != bot:
            self.add_error(
                "preview_channel",
                "Selected preview channel must belong to the chosen bot.",
            )
        return cleaned_data