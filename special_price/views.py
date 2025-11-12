from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Prefetch
from .models import SpecialPriceType, SpecialPriceHistory
from .forms import SpecialPriceUpdateForm, SpecialPriceTypeForm


def special_price_dashboard(request):
    """
    Display a dashboard showing all special price types with latest prices.
    """
    special_price_types = SpecialPriceType.objects.prefetch_related(
        Prefetch(
            'special_price_histories',
            queryset=SpecialPriceHistory.objects.order_by('-created_at')
        )
    ).select_related('source_currency', 'target_currency').all()
    
    context = {
        'special_price_types': special_price_types
    }
    return render(request, 'special_price/special_price_dashboard.html', context)


def update_special_price(request, special_price_type_id):
    special_price_type = get_object_or_404(SpecialPriceType, id=special_price_type_id)
    
    # Get latest price history if exists
    latest_price = SpecialPriceHistory.objects.filter(special_price_type=special_price_type).first()
    
    if request.method == 'POST':
        form = SpecialPriceUpdateForm(request.POST)
        if form.is_valid():
            price_history = form.save(commit=False)
            price_history.special_price_type = special_price_type
            price_history.save()
            messages.success(request, f'Special price updated successfully for {special_price_type.name}')
            return redirect('special_price:dashboard')
    else:
        initial_data = {}
        if latest_price:
            initial_data = {
                'price': latest_price.price
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
