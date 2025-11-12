from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from category.models import PriceType, Category
from .models import PriceHistory
from .forms import PriceUpdateForm, CategoryPriceUpdateForm


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
            price_history.save()
            messages.success(request, f'Price updated successfully for {price_type.name}')
            return redirect('dashboard:home')
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
                    
                    PriceHistory.objects.create(
                        price_type=price_type,
                        price=price,
                        notes=notes
                    )
            
            messages.success(request, f'All prices updated successfully for category {category.name}')
            return redirect('dashboard:home')
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