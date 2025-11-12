from django import forms
from .models import SpecialPriceHistory, SpecialPriceType
from category.models import Currency


class SpecialPriceUpdateForm(forms.ModelForm):
    class Meta:
        model = SpecialPriceHistory
        fields = ['price', 'notes']
        widgets = {
            'price': forms.NumberInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter special price',
                'step': '0.01',
                'min': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control theme-input',
                'rows': 3,
                'placeholder': 'Enter any notes about this special price update (optional)'
            })
        }


class SpecialPriceTypeForm(forms.ModelForm):
    class Meta:
        model = SpecialPriceType
        fields = ['name', 'source_currency', 'target_currency', 'trade_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control theme-input',
                'placeholder': 'Enter special price type name (e.g., Special Price: Pound)'
            }),
            'source_currency': forms.Select(attrs={
                'class': 'form-select theme-input'
            }),
            'target_currency': forms.Select(attrs={
                'class': 'form-select theme-input'
            }),
            'trade_type': forms.Select(attrs={
                'class': 'form-select theme-input'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control theme-input',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
        }

