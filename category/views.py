from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Category, PriceType
from .forms import CategoryForm, PriceTypeForm


def category_dashboard(request):
    """Show categories and embedded forms for quick add (but links go to dedicated pages).

    The template expects `categories` with `price_types` prefetched.
    """
    categories = Category.objects.prefetch_related('price_types').all()
    return render(request, 'category/category_dashboard.html', {'categories': categories})


def add_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('category:category_dashboard')
    else:
        form = CategoryForm()
    return render(request, 'category/category_form.html', {'form': form, 'title': 'Add Category'})


def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('category:category_dashboard')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category/category_form.html', {'form': form, 'title': 'Edit Category', 'category': category})


def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        return redirect('category:category_dashboard')
    return render(request, 'category/category_confirm_delete.html', {'category': category})


def add_pricetype(request, category_pk):
    category = get_object_or_404(Category, pk=category_pk)
    if request.method == 'POST':
        form = PriceTypeForm(request.POST, category=category)
        if form.is_valid():
            pt = form.save(commit=False)
            pt.category = category
            pt.save()
            return redirect('category:category_dashboard')
    else:
        form = PriceTypeForm(category=category)
    return render(request, 'category/pricetype_form.html', {'form': form, 'title': f'Add Price Type to {category.name}', 'category': category})


def edit_pricetype(request, pk):
    pt = get_object_or_404(PriceType, pk=pk)
    if request.method == 'POST':
        form = PriceTypeForm(request.POST, instance=pt, category=pt.category)
        if form.is_valid():
            form.save()
            return redirect('category:category_dashboard')
    else:
        form = PriceTypeForm(instance=pt, category=pt.category)
    return render(request, 'category/pricetype_form.html', {'form': form, 'title': 'Edit Price Type', 'category': pt.category})


def delete_pricetype(request, pk):
    pt = get_object_or_404(PriceType, pk=pk)
    if request.method == 'POST':
        pt.delete()
        return redirect('category:category_dashboard')
    return render(request, 'category/pricetype_confirm_delete.html', {'pricetype': pt})
