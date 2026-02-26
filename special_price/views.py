from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Prefetch
from .models import SpecialPriceType, SpecialPriceHistory
from .forms import SpecialPriceUpdateForm, SpecialPriceUpdateDoubleForm, SpecialPriceTypeForm
from setting.utils import log_event


def special_price_dashboard(request):
    """
    Display a dashboard showing all special price types with latest prices.
    Pinned at top: قیمت خرید ویژه نقدی و حسابی, قیمت فروش ویژه نقدی و حسابی (double-price types).
    Rest below.
    """
    all_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            'special_price_histories',
            queryset=SpecialPriceHistory.objects.order_by('-created_at')
        )
    ).select_related('source_currency', 'target_currency').all()

    # Pinned: double-price GBP types (Buy first, then Sell)
    PINNED_SLUGS = ('special-gbp-buy', 'special-gbp-sell')
    pinned_special_price_types = [
        t for t in all_types
        if getattr(t, 'slug', None) in PINNED_SLUGS
    ]
    pinned_special_price_types.sort(
        key=lambda t: (0 if getattr(t, 'slug') == 'special-gbp-buy' else 1)
    )

    # Others: exclude pinned
    pinned_ids = {t.id for t in pinned_special_price_types}
    other_special_price_types = [t for t in all_types if t.id not in pinned_ids]

    context = {
        'pinned_special_price_types': pinned_special_price_types,
        'other_special_price_types': other_special_price_types,
    }
    return render(request, 'special_price/special_price_dashboard.html', context)


def update_special_price(request, special_price_type_id):
    special_price_type = get_object_or_404(SpecialPriceType, id=special_price_type_id)

    # Get latest price history if exists
    latest_price = SpecialPriceHistory.objects.filter(special_price_type=special_price_type).first()

    if special_price_type.is_double_price:
        # Double-price form: Cash + Account
        if request.method == 'POST':
            form = SpecialPriceUpdateDoubleForm(request.POST)
            if form.is_valid():
                cash_price = form.cleaned_data['cash_price']
                account_price = form.cleaned_data['account_price']
                notes = form.cleaned_data.get('notes') or ''
                price_history = SpecialPriceHistory(
                    special_price_type=special_price_type,
                    price=cash_price,  # for analytics/API compatibility
                    cash_price=cash_price,
                    account_price=account_price,
                    notes=notes or None,
                )
                price_history.save()
                old_cash = latest_price.cash_price if latest_price else None
                old_account = latest_price.account_price if latest_price else None
                log_event(
                    level='INFO',
                    source='system',
                    message=f'Special price updated: {special_price_type.name}',
                    details=f'Old cash: {old_cash}, account: {old_account}. New cash: {cash_price}, account: {account_price}. Notes: {notes or "None"}',
                    user=request.user if request.user.is_authenticated else None,
                )
                messages.success(request, f'Special price updated successfully for {special_price_type.name}')
                return redirect('finalize:dashboard')
        else:
            initial = {}
            if latest_price:
                initial = {
                    'cash_price': latest_price.cash_price or latest_price.price,
                    'account_price': latest_price.account_price or latest_price.price,
                    'notes': latest_price.notes or '',
                }
            form = SpecialPriceUpdateDoubleForm(initial=initial)
    else:
        # Single-price form
        if request.method == 'POST':
            form = SpecialPriceUpdateForm(request.POST)
            if form.is_valid():
                price_history = form.save(commit=False)
                price_history.special_price_type = special_price_type
                old_price = latest_price.price if latest_price else None
                price_history.save()

                log_event(
                    level='INFO',
                    source='system',
                    message=f'Special price updated: {special_price_type.name}',
                    details=f'Old price: {old_price}, New price: {price_history.price}, Notes: {price_history.notes or "None"}',
                    user=request.user if request.user.is_authenticated else None
                )

                messages.success(request, f'Special price updated successfully for {special_price_type.name}')
                return redirect('finalize:dashboard')
        else:
            initial_data = {}
            if latest_price:
                initial_data = {
                    'price': latest_price.price,
                    'notes': latest_price.notes or '',
                }
            form = SpecialPriceUpdateForm(initial=initial_data)

    context = {
        'form': form,
        'special_price_type': special_price_type,
        'latest_price': latest_price
    }
    return render(request, 'special_price/update_special_price.html', context)


def special_price_history(request, special_price_type_id):
    special_price_type = get_object_or_404(SpecialPriceType, id=special_price_type_id)
    histories = SpecialPriceHistory.objects.filter(special_price_type=special_price_type)
    
    context = {
        'special_price_type': special_price_type,
        'histories': histories
    }
    return render(request, 'special_price/special_price_history.html', context)


def add_special_price_type(request):
    """Add a new special price type"""
    if request.method == 'POST':
        form = SpecialPriceTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Special price type "{form.cleaned_data["name"]}" added successfully!')
            return redirect('special_price:dashboard')
    else:
        form = SpecialPriceTypeForm()
    
    context = {
        'form': form,
        'title': 'Add New Special Price Type'
    }
    return render(request, 'special_price/special_price_type_form.html', context)


def edit_special_price_type(request, special_price_type_id):
    """Edit an existing special price type"""
    special_price_type = get_object_or_404(SpecialPriceType, id=special_price_type_id)
    
    if request.method == 'POST':
        form = SpecialPriceTypeForm(request.POST, instance=special_price_type)
        if form.is_valid():
            form.save()
            messages.success(request, f'Special price type "{form.cleaned_data["name"]}" updated successfully!')
            return redirect('special_price:dashboard')
    else:
        form = SpecialPriceTypeForm(instance=special_price_type)
    
    context = {
        'form': form,
        'special_price_type': special_price_type,
        'title': f'Edit Special Price Type: {special_price_type.name}'
    }
    return render(request, 'special_price/special_price_type_form.html', context)


def delete_special_price_type(request, special_price_type_id):
    """Delete a special price type"""
    special_price_type = get_object_or_404(SpecialPriceType, id=special_price_type_id)
    
    if request.method == 'POST':
        name = special_price_type.name
        special_price_type.delete()
        messages.success(request, f'Special price type "{name}" deleted successfully!')
        return redirect('special_price:dashboard')
    
    context = {
        'special_price_type': special_price_type
    }
    return render(request, 'special_price/special_price_type_confirm_delete.html', context)
