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


class SpecialPriceUpdateDoubleForm(forms.Form):
    """Form for double-price types: Cash (نقدی) and Account (حسابی) prices."""

    cash_price = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control theme-input rounded-2xl',
            'placeholder': 'قیمت نقدی',
            'step': '0.01',
            'min': '0',
        }),
        label='قیمت نقدی (Cash)',
    )
    account_price = forms.DecimalField(
        max_digits=20,
        decimal_places=2,
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control theme-input rounded-2xl',
            'placeholder': 'قیمت حسابی',
            'step': '0.01',
            'min': '0',
        }),
        label='قیمت حسابی (Account)',
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control theme-input rounded-2xl',
            'rows': 3,
            'placeholder': 'Enter any notes about this special price update (optional)',
        }),
        label='Notes',
    )


class SpecialPriceTypeForm(forms.ModelForm):
    class Meta:
        model = SpecialPriceType
        fields = ['name', 'source_currency', 'target_currency', 'trade_type', 'is_double_price', 'description']
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
            'is_double_price': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control theme-input',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
        }

