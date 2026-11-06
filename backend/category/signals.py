# Cache signals removed - no caching is used in this application
# If you need to add signals for other purposes, you can add them here

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from .models import Currency


@receiver(post_migrate)
def create_default_currencies_on_startup(sender, **kwargs):
    """
    Ensure default currencies are created when the app starts.
    This runs after migrations to guarantee currencies exist.
    """
    # Only run for the category app
    if sender.name != 'category':
        return
    
    # List of commonly used currencies in the website
    default_currencies = [
        {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
        {'code': 'USDT', 'name': 'Tether', 'symbol': 'USDT'},
        {'code': 'BTC', 'name': 'Bitcoin', 'symbol': 'BTC'},
        {'code': 'ETH', 'name': 'Ethereum', 'symbol': 'ETH'},
        {'code': 'BNB', 'name': 'BNB', 'symbol': 'BNB'},
        {'code': 'EUR', 'name': 'Euro', 'symbol': 'EUR'},
        {'code': 'GBP', 'name': 'British Pound', 'symbol': 'GBP'},
        {'code': 'AUD', 'name': 'Australian Dollar', 'symbol': 'AUD'},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'CAD'},
        {'code': 'CHF', 'name': 'Swiss Franc', 'symbol': 'CHF'},
        {'code': 'CNY', 'name': 'Chinese Yuan', 'symbol': 'CNY'},
        {'code': 'TRY', 'name': 'Turkish Lira', 'symbol': 'TRY'},
        {'code': 'IRR', 'name': 'Iranian Rial', 'symbol': 'IRR'},
        {'code': 'IRT', 'name': 'Iranian Toman', 'symbol': 'IRT'},
        {'code': 'AED', 'name': 'UAE Dirham', 'symbol': 'AED'},
        {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': 'JPY'},
        {'code': 'RUB', 'name': 'Russian Ruble', 'symbol': 'RUB'},
        {'code': 'IQD', 'name': 'Iraqi Dinar', 'symbol': 'IQD'},
        {'code': 'XAU', 'name': 'Gold', 'symbol': 'XAU'},
    ]
    
    # Create currencies if they don't exist
    for currency_data in default_currencies:
        Currency.objects.update_or_create(
            code=currency_data['code'],
            defaults={'name': currency_data['name'], 'symbol': currency_data['symbol']}
        )

