from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from category.models import PriceType, Category
from .models import PriceHistory
from .forms import PriceUpdateForm, CategoryPriceUpdateForm
from setting.utils import log_event
from core.sorting import (
    sort_gbp_price_types,
    sort_tether_price_types,
    sort_categories,
)


def _ensure_tether_column_price_types() -> None:
    """
    Keep Tether-relevant cross-currency rates under the Tether category.
    """
    tether_category = Category.objects.filter(
        name__iregex=r"(تتر|tether|usdt)"
    ).first()
    if not tether_category:
        return

    tether_related = PriceType.objects.select_related(
        "source_currency", "target_currency", "category"
    ).filter(
        category__name__iregex=r"(پوند|pound|gbp|تتر|tether|usdt)"
    )

    ids_to_move = []
    for pt in tether_related:
        name_lower = (pt.name or "").lower()
        source_code = (getattr(pt.source_currency, "code", "") or "").upper()
        target_code = (getattr(pt.target_currency, "code", "") or "").upper()
        involves_tether = "USDT" in {source_code, target_code} or any(
            token in name_lower for token in ("تتر", "tether", "usdt")
        )
        is_tether_cross = (
            ("USDT" in {source_code, target_code} and {"TRY", "EUR", "AED", "GBP"} & {source_code, target_code})
            or any(token in name_lower for token in ("تتر", "tether", "usdt"))
            and any(token in name_lower for token in ("لیر", "یورو", "درهم", "پوند", "lira", "euro", "dirham", "pound", "gbp"))
        )
        is_requested_cross = (
            source_code in {"TRY", "EUR", "AED"}
            or target_code in {"TRY", "EUR", "AED"}
            or any(token in name_lower for token in ("لیر", "یورو", "درهم", "lira", "euro", "dirham"))
        )
        should_move_to_tether = involves_tether or is_tether_cross or is_requested_cross
        is_core_pound_row = (
            source_code == "GBP"
            and target_code in {"IRT", "IRR"}
            and any(token in name_lower for token in ("خرید نقدی", "خرید از حساب", "فروش نقدی", "فروش از حساب", "فروش رسمی", "cash", "account", "official"))
        )
        if should_move_to_tether and not is_core_pound_row and pt.category_id != tether_category.id:
            ids_to_move.append(pt.id)

    if ids_to_move:
        PriceType.objects.filter(id__in=ids_to_move).update(category=tether_category)


def price_dashboard(request):
    """
    Display a dashboard showing all categories and their price types with latest prices.
    """
    _ensure_tether_column_price_types()

    categories = Category.objects.prefetch_related(
        Prefetch(
            'price_types',
            queryset=PriceType.objects.prefetch_related('price_histories').select_related(
                'source_currency', 'target_currency'
            )
        )
    ).all()
    
    categories = sort_categories(categories)
    
    context = {
        'categories': categories
    }
    return render(request, 'change_price/price_dashboard.html', context)


def update_price(request, price_type_id):
    price_type = get_object_or_404(PriceType, id=price_type_id)
    
    # Get latest price history if exists
    latest_price = PriceHistory.objects.filter(price_type=price_type).first()
    
    if request.method == 'POST':
        form = PriceUpdateForm(request.POST)
        if form.is_valid():
            price_history = form.save(commit=False)
            price_history.price_type = price_type
            old_price = latest_price.price if latest_price else None
            price_history.save()
            
            # Log the price update
            log_event(
                level='INFO',
                source='system',
                message=f'Price updated for {price_type.name} ({price_type.category.name})',
                details=f'Old price: {old_price}, New price: {price_history.price}, Notes: {price_history.notes or "None"}',
                user=request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f'Price updated successfully for {price_type.name}')
            return redirect('finalize:dashboard')
    else:
        initial_data = {}
        if latest_price:
            initial_data = {
                'price': latest_price.price
            }
        form = PriceUpdateForm(initial=initial_data)
    
    context = {
        'form': form,
        'price_type': price_type,
        'latest_price': latest_price
    }
    return render(request, 'change_price/update_price.html', context)


def price_history(request, price_type_id):
    price_type = get_object_or_404(PriceType, id=price_type_id)
    histories = PriceHistory.objects.filter(price_type=price_type)
    
    context = {
        'price_type': price_type,
        'histories': histories
    }
    return render(request, 'change_price/price_history.html', context)


def update_category_prices(request, category_id):
    _ensure_tether_column_price_types()
    category = get_object_or_404(Category, id=category_id)
    price_types = PriceType.objects.filter(category=category)
    
    # Sort price types based on category type
    category_name_lower = category.name.lower()
    if 'پوند' in category.name or 'pound' in category_name_lower or 'gbp' in category_name_lower:
        price_types = sort_gbp_price_types(price_types)
    elif 'تتر' in category.name or 'tether' in category_name_lower or 'usdt' in category_name_lower:
        price_types = sort_tether_price_types(price_types)
    
    # Get latest prices for all price types
    latest_prices = {
        pt.id: PriceHistory.objects.filter(price_type=pt).first()
        for pt in price_types
    }
    
    if request.method == 'POST':
        form = CategoryPriceUpdateForm(category, request.POST)
        if form.is_valid():
            with transaction.atomic():
                notes = form.cleaned_data.pop('notes')
                updated_prices = []
                for price_type in price_types:
                    # Get the submitted price, or use the previous price if empty
                    submitted_price = form.cleaned_data.get(f'price_{price_type.id}')
                    
                    # If no price was submitted (None for DecimalField when empty), use the latest price
                    if submitted_price is None:
                        latest = latest_prices[price_type.id]
                        if latest:
                            price = latest.price
                        else:
                            # If no previous price exists, skip this price type
                            continue
                    else:
                        price = submitted_price
                    
                    old_price = latest_prices[price_type.id].price if latest_prices[price_type.id] else None
                    PriceHistory.objects.create(
                        price_type=price_type,
                        price=price,
                        notes=notes
                    )
                    updated_prices.append(f"{price_type.name}: {old_price} → {price}")
            
            # Log the category price update
            log_event(
                level='INFO',
                source='system',
                message=f'Category prices updated: {category.name}',
                details=f'Updated {len(updated_prices)} price(s). Changes: {"; ".join(updated_prices)}. Notes: {notes or "None"}',
                user=request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f'All prices updated successfully for category {category.name}')
            return redirect('finalize:dashboard')
    else:
        initial_data = {}
        # Pre-fill form with latest prices
        for price_type in price_types:
            latest = latest_prices[price_type.id]
            if latest:
                initial_data[f'price_{price_type.id}'] = latest.price
        
        form = CategoryPriceUpdateForm(category, initial=initial_data)
    
    context = {
        'form': form,
        'category': category,
        'price_types': price_types,
        'latest_prices': latest_prices
    }
    return render(request, 'change_price/update_category_prices.html', context)