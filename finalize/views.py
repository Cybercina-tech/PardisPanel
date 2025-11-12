from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Prefetch, Max
from django.utils import timezone
from datetime import timedelta
from category.models import Category, PriceType
from change_price.models import PriceHistory
from special_price.models import SpecialPriceType, SpecialPriceHistory
from telegram_app.models import TelegramChannel
from price_publisher.services.publisher import (
    PricePublicationError,
    PricePublisherService,
)
from .models import Finalization, FinalizedPriceHistory, SpecialPriceFinalization


@login_required
def finalize_dashboard(request):
    """
    Display dashboard showing:
    - Prices that have recently changed and are not yet finalized
    - All categories with links to their update pages
    - Special prices that are pending finalization
    """
    # Get all categories with their price types
    categories = Category.objects.prefetch_related(
        Prefetch(
            'price_types',
            queryset=PriceType.objects.prefetch_related('price_histories').select_related(
                'source_currency', 'target_currency'
            )
        )
    ).all()
    
    # Find prices that are not finalized yet
    # A price is not finalized if there's a PriceHistory entry that doesn't have a FinalizedPriceHistory
    # Get the latest finalization for each category to determine cutoff
    pending_prices = []
    pending_by_category = {}
    
    for category in categories:
        # Get latest finalization for this category
        latest_finalization = Finalization.objects.filter(
            category=category
        ).order_by('-finalized_at').first()
        
        if latest_finalization:
            # Get all price histories that were finalized in the latest finalization
            finalized_history_ids = set(
                latest_finalization.finalized_prices.values_list('price_history_id', flat=True)
            )
        else:
            finalized_history_ids = set()
        
        # Get all price types for this category
        price_types = category.price_types.all()
        category_pending = []
        
        for price_type in price_types:
            # Get latest price history
            latest_price = price_type.price_histories.first()
            if latest_price:
                # Check if this price history is finalized
                if latest_price.id not in finalized_history_ids:
                    category_pending.append({
                        'price_type': price_type,
                        'price_history': latest_price,
                        'has_older_finalized': len(finalized_history_ids) > 0
                    })
        
        if category_pending:
            pending_by_category[category] = category_pending
    
    # Get pending special prices
    # A special price is pending if it doesn't have a finalization record
    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            'special_price_histories',
            queryset=SpecialPriceHistory.objects.order_by('-created_at')
        )
    ).select_related('source_currency', 'target_currency').all()
    
    pending_special_prices = []
    for special_price_type in special_price_types:
        latest_price = special_price_type.special_price_histories.first()
        if latest_price:
            # Check if this special price history is finalized
            is_finalized = SpecialPriceFinalization.objects.filter(
                special_price_history=latest_price
            ).exists()
            
            if not is_finalized:
                pending_special_prices.append({
                    'special_price_type': special_price_type,
                    'special_price_history': latest_price
                })
    
    context = {
        'categories': categories,
        'pending_by_category': pending_by_category,
        'has_pending': len(pending_by_category) > 0,
        'pending_special_prices': pending_special_prices,
        'has_pending_special': len(pending_special_prices) > 0
    }
    
    return render(request, 'finalize/finalize_dashboard.html', context)


@login_required
def finalize_category(request, category_id):
    """
    Finalize all pending prices in a category and send them to Telegram.
    """
    category = get_object_or_404(Category, id=category_id)
    
    # Get all active Telegram channels
    channels = TelegramChannel.objects.filter(is_active=True).select_related('bot')
    
    if request.method == 'POST':
        channel_id = request.POST.get('channel_id')
        notes = request.POST.get('notes', '')
        
        if not channel_id:
            messages.error(request, 'Please select a Telegram channel.')
            return redirect('finalize:dashboard')
        
        channel = get_object_or_404(TelegramChannel, id=channel_id, is_active=True)
        
        # Get latest finalization for this category to determine which prices are pending
        latest_finalization = Finalization.objects.filter(
            category=category
        ).order_by('-finalized_at').first()
        
        if latest_finalization:
            finalized_history_ids = set(
                latest_finalization.finalized_prices.values_list('price_history_id', flat=True)
            )
        else:
            finalized_history_ids = set()
        
        # Get all price types for this category
        price_types = PriceType.objects.filter(category=category).select_related(
            'source_currency', 'target_currency'
        )
        
        # Get latest price histories that are not finalized
        pending_prices = []
        for price_type in price_types:
            latest_price = price_type.price_histories.first()
            if latest_price and latest_price.id not in finalized_history_ids:
                pending_prices.append({
                    'price_type': price_type,
                    'price_history': latest_price
                })
        
        if not pending_prices:
            messages.warning(request, f'No pending prices to finalize for category "{category.name}".')
            return redirect('finalize:dashboard')
        
        price_items = [
            (item['price_type'], item['price_history']) for item in pending_prices
        ]

        notes_text = notes.strip() if notes else None

        publisher = PricePublisherService()
        message_sent = False
        image_caption = None
        publication_response = ""

        try:
            publication = publisher.publish_category_prices(
                category=category,
                price_items=price_items,
                channel=channel,
                notes=notes_text,
            )
            message_sent = publication.success
            image_caption = publication.caption
            publication_response = publication.response

            if not publication.success:
                messages.warning(
                    request,
                    f'Prices finalized but failed to send image to Telegram: {publication.response}'
                )
        except PricePublicationError as exc:
            publication_response = str(exc)
            messages.warning(
                request,
                f'Prices finalized but image publication failed: {publication_response}'
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            publication_response = str(exc)
            messages.warning(
                request,
                f'Prices finalized but encountered an unexpected error during publication: {publication_response}'
            )

        # Create finalization record
        with transaction.atomic():
            finalization = Finalization.objects.create(
                category=category,
                channel=channel if message_sent else None,
                finalized_by=request.user,
                message_sent=message_sent,
                image_caption=image_caption if message_sent else None,
                telegram_response=publication_response or None,
                notes=notes
            )
            
            # Create FinalizedPriceHistory entries
            for item in pending_prices:
                FinalizedPriceHistory.objects.create(
                    finalization=finalization,
                    price_history=item['price_history']
                )
        
        if message_sent:
            messages.success(
                request,
                f'Successfully finalized and published {len(pending_prices)} prices for category "{category.name}" as an image on Telegram.'
            )
        else:
            messages.success(
                request,
                f'Successfully finalized {len(pending_prices)} prices for category "{category.name}". Telegram image publication failed.'
            )
        
        return redirect('finalize:dashboard')
    
    # GET request - show confirmation form
    # Get latest finalization to determine pending prices
    latest_finalization = Finalization.objects.filter(
        category=category
    ).order_by('-finalized_at').first()
    
    if latest_finalization:
        finalized_history_ids = set(
            latest_finalization.finalized_prices.values_list('price_history_id', flat=True)
        )
    else:
        finalized_history_ids = set()
    
    # Get pending prices
    price_types = PriceType.objects.filter(category=category).select_related(
        'source_currency', 'target_currency'
    )
    pending_prices = []
    for price_type in price_types:
        latest_price = price_type.price_histories.first()
        if latest_price and latest_price.id not in finalized_history_ids:
            pending_prices.append({
                'price_type': price_type,
                'price_history': latest_price
            })
    
    if not pending_prices:
        messages.info(request, f'No pending prices to finalize for category "{category.name}".')
        return redirect('finalize:dashboard')
    
    context = {
        'category': category,
        'pending_prices': pending_prices,
        'channels': channels
    }
    
    return render(request, 'finalize/finalize_category.html', context)


@login_required
def finalize_special_price(request, special_price_history_id):
    """
    Finalize a special price individually and send it to Telegram.
    Special prices are posted individually, not in bulk.
    """
    special_price_history = get_object_or_404(SpecialPriceHistory, id=special_price_history_id)
    special_price_type = special_price_history.special_price_type
    
    # Get all active Telegram channels
    channels = TelegramChannel.objects.filter(is_active=True).select_related('bot')
    
    # Check if this price is already finalized
    existing_finalization = SpecialPriceFinalization.objects.filter(
        special_price_history=special_price_history
    ).first()
    
    if request.method == 'POST':
        channel_id = request.POST.get('channel_id')
        notes = request.POST.get('notes', '')
        
        if not channel_id:
            messages.error(request, 'Please select a Telegram channel.')
            return redirect('finalize:dashboard')
        
        channel = get_object_or_404(TelegramChannel, id=channel_id, is_active=True)
        
        # Build message text for individual special price
        currency_pair = f"{special_price_type.source_currency.code}/{special_price_type.target_currency.code}"
        trade_type = special_price_type.get_trade_type_display()
        
        notes_text = notes.strip() if notes else None

        publisher = PricePublisherService()
        message_sent = False
        image_caption = None
        publication_response = ""

        try:
            publication = publisher.publish_special_price(
                special_price_type=special_price_type,
                price_history=special_price_history,
                channel=channel,
                notes=notes_text,
            )
            message_sent = publication.success
            image_caption = publication.caption
            publication_response = publication.response

            if not publication.success:
                messages.warning(
                    request,
                    f'Special price finalized but failed to send image to Telegram: {publication.response}'
                )
        except PricePublicationError as exc:
            publication_response = str(exc)
            messages.warning(
                request,
                f'Special price finalized but image publication failed: {publication_response}'
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            publication_response = str(exc)
            messages.warning(
                request,
                f'Special price finalized but encountered an unexpected error during publication: {publication_response}'
            )

        # Create finalization record
        finalization = SpecialPriceFinalization.objects.create(
            special_price_history=special_price_history,
            channel=channel if message_sent else None,
            finalized_by=request.user,
            message_sent=message_sent,
            image_caption=image_caption if message_sent else None,
            telegram_response=publication_response or None,
            notes=notes
        )

        if message_sent:
            messages.success(
                request,
                f'Successfully finalized and published special price "{special_price_type.name}" as an image on Telegram.'
            )
        else:
            messages.success(
                request,
                f'Successfully finalized special price "{special_price_type.name}". Telegram image publication failed.'
            )
        
        return redirect('finalize:dashboard')
    
    # GET request - show confirmation form
    context = {
        'special_price_history': special_price_history,
        'special_price_type': special_price_type,
        'channels': channels,
        'is_already_finalized': existing_finalization is not None,
        'existing_finalization': existing_finalization
    }
    
    return render(request, 'finalize/finalize_special_price.html', context)
