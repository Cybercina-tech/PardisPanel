from django.db import models
from django.utils import timezone


class PriceThemeState(models.Model):
    """
    Tracks the last price theme index used when rendering channel images.

    A single row with key ``price_theme`` is created automatically and updated
    each time a new image is rendered so that themes cycle through sequentially.
    """

    key = models.CharField(max_length=50, unique=True)
    last_index = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Price Theme State"
        verbose_name_plural = "Price Theme States"

    @classmethod
    def get_or_create_theme_state(cls):
        return cls.objects.get_or_create(key="price_theme", defaults={"last_index": 0})


class Log(models.Model):
    """
    Stores application logs from various sources (Telegram, Finalize, etc.)
    """
    
    LEVEL_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    SOURCE_CHOICES = [
        ('telegram', 'Telegram'),
        ('finalize', 'Finalize'),
        ('price_publisher', 'Price Publisher'),
        ('template_editor', 'Template Editor'),
        ('system', 'System'),
        ('other', 'Other'),
    ]
    
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='INFO')
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='system')
    message = models.TextField(verbose_name="Message")
    details = models.TextField(blank=True, null=True, verbose_name="Additional Details")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    user = models.ForeignKey(
        'accounts.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        verbose_name="User"
    )
    
    class Meta:
        verbose_name = "Log"
        verbose_name_plural = "Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['level', '-created_at']),
            models.Index(fields=['source', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.source} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"

