from django.shortcuts import render
from django.db.models import Max, Count, Q
from django.utils import timezone
from datetime import timedelta
from category.models import Category, PriceType
from change_price.models import PriceHistory
from telegram_app.models import TelegramBot, TelegramChannel


def home(request):
    """
    Renders the home dashboard with categories, price types, and latest prices.
    Includes dynamic metrics calculated from the database.
    """
    categories = Category.objects.prefetch_related(
        'price_types',
        'price_types__price_histories'
    ).all()
    
    # Calculate dynamic metrics
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    
    # 1. Highest posted price (across all price histories)
    highest_price_obj = PriceHistory.objects.select_related('price_type').order_by('-price').first()
    highest_price = highest_price_obj.price if highest_price_obj else 0
    highest_price_label = highest_price_obj.price_type.name if highest_price_obj else "N/A"
    
    # 2. Price change over last 24 hours
    # Get all price types with their latest prices and prices from 24h ago
    price_changes = []
    price_types = PriceType.objects.prefetch_related('price_histories').all()
    
    for price_type in price_types:
        latest_price_history = price_type.price_histories.first()  # Already ordered by -created_at
        if latest_price_history:
            # Get price from 24 hours ago (or closest earlier price)
            # Order by -created_at to get the most recent price before 24h ago
            old_price_history = price_type.price_histories.filter(
                created_at__lte=twenty_four_hours_ago
            ).order_by('-created_at').first()
            
            if old_price_history and latest_price_history.created_at > twenty_four_hours_ago:
                current_price = float(latest_price_history.price)
                old_price = float(old_price_history.price)
                if old_price > 0:
                    change_percent = ((current_price - old_price) / old_price) * 100
                    change_amount = current_price - old_price
                    price_changes.append({
                        'name': price_type.name,
                        'current': current_price,
                        'old': old_price,
                        'change_percent': change_percent,
                        'change_amount': change_amount
                    })
    
    # Calculate average 24h change if we have data
    if price_changes:
        avg_24h_change = sum(p['change_percent'] for p in price_changes) / len(price_changes)
        # Find the biggest change
        biggest_change = max(price_changes, key=lambda x: abs(x['change_percent']))
    else:
        avg_24h_change = 0
        biggest_change = None
    
    # 3. Total number of bots
    total_bots = TelegramBot.objects.count()
    active_bots = TelegramBot.objects.filter(is_active=True).count()
    
    # 4. Other useful statistics
    total_channels = TelegramChannel.objects.count()
    active_channels = TelegramChannel.objects.filter(is_active=True).count()
    total_price_types = PriceType.objects.count()
    total_price_updates = PriceHistory.objects.count()
    
    # Latest price update time
    latest_update = PriceHistory.objects.select_related('price_type').order_by('-created_at').first()
    latest_update_time = latest_update.created_at if latest_update else None
    
    # Price updates in last 24 hours
    recent_updates = PriceHistory.objects.filter(created_at__gte=twenty_four_hours_ago).count()
    
    context = {
        'categories': categories,
        # Metrics for cards
        'highest_price': highest_price,
        'highest_price_label': highest_price_label,
        'avg_24h_change': avg_24h_change,
        'biggest_change': biggest_change,
        'total_bots': total_bots,
        'active_bots': active_bots,
        'total_channels': total_channels,
        'active_channels': active_channels,
        'total_price_types': total_price_types,
        'total_price_updates': total_price_updates,
        'latest_update_time': latest_update_time,
        'recent_updates': recent_updates,
    }
    
    return render(request, 'dashboard/dashboard.html', context)
