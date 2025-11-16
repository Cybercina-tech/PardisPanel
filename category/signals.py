from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Category, PriceType


def _clear_site_cache():
    # Clear entire site cache to ensure templates reflect latest categories/price types
    try:
        cache.clear()
    except Exception:
        # Fail silently; cache issues should not block writes
        pass


@receiver(post_save, sender=Category)
def invalidate_cache_on_category_save(sender, instance, **kwargs):
    _clear_site_cache()


@receiver(post_delete, sender=Category)
def invalidate_cache_on_category_delete(sender, instance, **kwargs):
    _clear_site_cache()


@receiver(post_save, sender=PriceType)
def invalidate_cache_on_pricetype_save(sender, instance, **kwargs):
    _clear_site_cache()


@receiver(post_delete, sender=PriceType)
def invalidate_cache_on_pricetype_delete(sender, instance, **kwargs):
    _clear_site_cache()

