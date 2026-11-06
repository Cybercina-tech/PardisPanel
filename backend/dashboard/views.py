from django.shortcuts import render
from django.db.models import Max, Count, Q, Prefetch
from django.utils import timezone
from datetime import timedelta
from category.models import Category, PriceType
from change_price.models import PriceHistory
from telegram_app.models import TelegramBot, TelegramChannel
from special_price.models import SpecialPriceType, SpecialPriceHistory


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
    
    # Get all special price types with their latest prices
    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            'special_price_histories',
            queryset=SpecialPriceHistory.objects.order_by('-created_at')
        )
    ).select_related('source_currency', 'target_currency').all()
    
    context = {
        'categories': categories,
        'special_price_types': special_price_types,
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


def dashboard2(request):
    """
    Renders the improved dashboard2 with modern Tailwind CSS styling, charts, and enhanced features.
    """
    from django.db.models import Avg, Max, Min
    
    categories = Category.objects.prefetch_related(
        'price_types',
        'price_types__price_histories'
    ).all()
    
    # Calculate dynamic metrics
    now = timezone.now()
    twenty_four_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)
    
    # 1. Highest posted price (across all price histories)
    highest_price_obj = PriceHistory.objects.select_related('price_type').order_by('-price').first()
    highest_price = highest_price_obj.price if highest_price_obj else 0
    highest_price_label = highest_price_obj.price_type.name if highest_price_obj else "N/A"
    
    # 2. Price change over last 24 hours
    price_changes = []
    price_types = PriceType.objects.prefetch_related('price_histories').all()
    
    for price_type in price_types:
        latest_price_history = price_type.price_histories.first()
        if latest_price_history:
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
                        'change_amount': change_amount,
                        'category': price_type.category.name if price_type.category else 'Uncategorized'
                    })
    
    # Calculate average 24h change if we have data
    if price_changes:
        avg_24h_change = sum(p['change_percent'] for p in price_changes) / len(price_changes)
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
    
    # Get all special price types with their latest prices
    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            'special_price_histories',
            queryset=SpecialPriceHistory.objects.order_by('-created_at')
        )
    ).select_related('source_currency', 'target_currency').all()
    
    # ===== NEW FEATURES FOR CHARTS AND ENHANCEMENTS =====
    
    # Chart Data: Top 10 price types with 24h price history
    top_price_types = PriceType.objects.annotate(
        latest_price_count=Count('price_histories')
    ).filter(price_histories__created_at__gte=twenty_four_hours_ago).distinct()[:10]
    
    # Prepare chart data for 24h price trends
    chart_data_24h = []
    for price_type in top_price_types:
        histories = price_type.price_histories.filter(
            created_at__gte=twenty_four_hours_ago
        ).order_by('created_at')[:50]  # Limit to avoid too many points
        
        if histories.count() > 0:
            chart_data_24h.append({
                'label': price_type.name,
                'data': [
                    {
                        'x': h.created_at.isoformat(),
                        'y': float(h.price)
                    }
                    for h in histories
                ]
            })
    
    # Category comparison data (average prices per category)
    category_avg_prices = []
    for category in categories:
        category_price_types = category.price_types.all()
        if category_price_types.exists():
            latest_prices = []
            for pt in category_price_types:
                latest = pt.price_histories.first()
                if latest:
                    latest_prices.append(float(latest.price))
            
            if latest_prices:
                category_avg_prices.append({
                    'name': category.name,
                    'avg_price': sum(latest_prices) / len(latest_prices),
                    'count': len(latest_prices)
                })
    
    # Recent updates timeline (last 10 updates)
    recent_updates_list = PriceHistory.objects.select_related(
        'price_type', 'price_type__category'
    ).order_by('-created_at')[:10]
    
    recent_updates_data = [
        {
            'price_type': update.price_type.name,
            'category': update.price_type.category.name if update.price_type.category else 'Uncategorized',
            'price': float(update.price),
            'created_at': update.created_at.isoformat(),
            'time_ago': str(now - update.created_at).split('.')[0] if update.created_at else ''
        }
        for update in recent_updates_list
    ]
    
    # Price distribution data (for histogram)
    all_latest_prices = [
        float(pt.price_histories.first().price)
        for pt in PriceType.objects.prefetch_related('price_histories').all()
        if pt.price_histories.exists()
    ]
    
    # Update frequency stats (last 7 days)
    update_frequency = []
    for day in range(7):
        day_start = now - timedelta(days=day+1)
        day_end = now - timedelta(days=day)
        count = PriceHistory.objects.filter(
            created_at__gte=day_start,
            created_at__lt=day_end
        ).count()
        update_frequency.append({
            'date': day_start.date().isoformat(),
            'count': count
        })
    update_frequency.reverse()  # Oldest first
    
    context = {
        'categories': categories,
        'special_price_types': special_price_types,
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
        'price_changes': price_changes,
        # Chart data (will be JSON encoded by json_script template filter)
        'chart_data_24h_json': chart_data_24h,
        'category_avg_prices_json': category_avg_prices,
        'recent_updates_json': recent_updates_data,
        'update_frequency_json': update_frequency,
        'price_distribution_json': all_latest_prices,
    }
    
    return render(request, 'dashboard/dashboard2.html', context)