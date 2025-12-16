from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from category.models import PriceType, Category
from .models import PriceHistory
from .forms import PriceUpdateForm, CategoryPriceUpdateForm
from setting.utils import log_event


def sort_gbp_price_types(price_types):
    """
    Sort price types for GBP/Pound category in specific order:
    1. خرید نقدی (Buy Cash)
    2. خرید حسابی (Buy Account)
    3. فروش نقد (Sell Cash)
    4. فروش حسابی (Sell Account)
    5. فروش رسمی (Sell Official)
    """
    if not price_types:
        return price_types
    
    price_types_list = list(price_types)
    
    def get_sort_key(price_type):
        name = price_type.name
        name_lower = name.lower()
        trade_type = price_type.trade_type.lower()
        
        # Buy types - order: 1. خرید نقدی, 2. خرید حسابی
        if trade_type == 'buy':
            # Check for خرید نقدی first (contains 'نقدی' or 'cash')
            if 'نقدی' in name or 'cash' in name_lower:
                return 1  # خرید نقدی
            # Check for خرید حسابی (contains 'حسابی', 'از حساب', or 'account')
            elif 'حسابی' in name or 'از حساب' in name or 'account' in name_lower:
                return 2  # خرید حسابی
            else:
                return 10  # Other buy types
        # Sell types - order: 3. فروش نقد, 4. فروش حسابی, 5. فروش رسمی
        elif trade_type == 'sell':
            # Check for فروش نقد/نقدی first (contains 'نقد' or 'cash')
            if 'نقد' in name or 'cash' in name_lower:
                return 3  # فروش نقد
            # Check for فروش حسابی (contains 'حسابی', 'از حساب', or 'account')
            elif 'حسابی' in name or 'از حساب' in name or 'account' in name_lower:
                return 4  # فروش حسابی
            # Check for فروش رسمی (contains 'رسمی' or 'official')
            elif 'رسمی' in name or 'official' in name_lower:
                return 5  # فروش رسمی
            else:
                return 20  # Other sell types
        else:
            return 30  # Unknown types
    
    return sorted(price_types_list, key=get_sort_key)


def sort_tether_price_types(price_types):
    """
    Sort price types for Tether category in specific order:
    1. خرید تتر تومان (Buy Tether Toman/IRR)
    2. فروش تتر تومان (Sell Tether Toman/IRR)
    3. خرید تتر پوند (Buy Tether GBP)
    4. فروش تتر پوند (Sell Tether GBP)
    """
    if not price_types:
        return price_types
    
    price_types_list = list(price_types)
    
    def get_sort_key(price_type):
        name_lower = price_type.name.lower()
        trade_type = price_type.trade_type.lower()
        
        # Check target currency
        target_code = getattr(price_type.target_currency, 'code', '').lower() if price_type.target_currency else ''
        target_name = price_type.target_currency.name.lower() if price_type.target_currency else ''
        has_toman = any(keyword in name_lower for keyword in ['تومان', 'تومن', 'toman', 'tmn']) or \
                    any(keyword in target_code for keyword in ['irr', 'irt']) or \
                    'تومان' in target_name or 'تومن' in target_name
        has_gbp = any(keyword in name_lower for keyword in ['پوند', 'pound', 'gbp']) or \
                  'gbp' in target_code or 'pound' in target_name or 'پوند' in target_name
        
        # Buy types
        if trade_type == 'buy':
            if has_toman:
                return 1  # خرید تتر تومان
            elif has_gbp:
                return 3  # خرید تتر پوند
            else:
                return 10  # Other buy types
        # Sell types
        elif trade_type == 'sell':
            if has_toman:
                return 2  # فروش تتر تومان
            elif has_gbp:
                return 4  # فروش تتر پوند
            else:
                return 20  # Other sell types
        else:
            return 30  # Unknown types
    
    return sorted(price_types_list, key=get_sort_key)


def price_dashboard(request):
    """
    Display a dashboard showing all categories and their price types with latest prices.
    """
    categories = Category.objects.prefetch_related(
        Prefetch(
            'price_types',
            queryset=PriceType.objects.prefetch_related('price_histories').select_related(
                'source_currency', 'target_currency'
            )
        )
    ).all()
    
    # Sort categories: پوند first, then تتر, then others
    def sort_key(category):
        name = category.name.lower()
        if 'پوند' in name or 'pound' in name or 'gbp' in name:
            return (0, name)
        elif 'تتر' in name or 'tether' in name or 'usdt' in name:
            return (1, name)
        else:
            return (2, name)
    
    categories = sorted(categories, key=sort_key)
    
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